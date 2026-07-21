import hashlib
import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.services.ai.FieldOpsAI.repositories.prompt_template_repository import (
    PromptTemplateRepository, 
    RepositoryError,
    TemplateConflictError,
    TemplateNotFoundError
)
from app.services.ai.FieldOpsAI.schemas.prompt_template import (
    PromptTemplateCreate,
    PromptTemplateUpdate,
    PromptTemplateResponse,
    PromptTemplateLookupResponse,
    AgentType,
    PromptChannel,
    PromptLanguage,
    _validate_jinja_variables
)
from pydantic import ValidationError

class RegistryServiceError(Exception):
    pass

class ConflictError(RegistryServiceError):
    pass

class NotFoundError(RegistryServiceError):
    pass

class TemplateValidationServiceError(
    RegistryServiceError
):
    """
    Raised when prompt-template validation fails.
    """

    pass
class ManagedPromptTemplateRegistry:

    def __init__(self, db: Session, tenant_id: str, actor_id: str, redis_client: Any, cache_ttl_seconds: int = 60):
        self.CACHE_TTL_SECONDS = 60
        if not tenant_id or not str(tenant_id).strip():
            raise ValueError("Invalid tenant_id")
        if not actor_id or not str(actor_id).strip():
            raise ValueError("Invalid actor_id")
        if cache_ttl_seconds != self.CACHE_TTL_SECONDS:
            raise ValueError("Prompt cache TTL must be 60 seconds.")
        self.db = db
        self.tenant_id = str(tenant_id).strip()
        self.actor_id = str(actor_id).strip()
        self.redis_client = redis_client
        self.cache_ttl_seconds = cache_ttl_seconds
        self.repo = PromptTemplateRepository(db, self.tenant_id)

    def _hash_tenant(self, tenant: str) -> str:
        return hashlib.sha256(tenant.encode('utf-8')).hexdigest()

    def _get_generation(self, tenant_hash: str) -> int:
        try:
            val = self.redis_client.get(f"prompt_gen:{tenant_hash}")
            return int(val) if val else 0
        except Exception:
            return 0

    def _increment_generation(self, tenant_hash: str) -> None:
        try:
            self.redis_client.incr(f"prompt_gen:{tenant_hash}")
        except Exception:
            pass

    def _invalidate_cache(self) -> None:
        tenant_hash = self._hash_tenant(
            self.tenant_id
        )

        self._increment_generation(
            tenant_hash
        )
    def _build_cache_key(self, prefix: str, **kwargs) -> str:
        tenant_hash = self._hash_tenant(self.tenant_id)
        platform_hash = self._hash_tenant("**platform**")
        t_gen = self._get_generation(tenant_hash)
        p_gen = self._get_generation(platform_hash)
        parts = [f"{k}:{v}" for k, v in sorted(kwargs.items())]
        return f"{prefix}:{tenant_hash}:{t_gen}:{platform_hash}:{p_gen}:" + ":".join(parts)

    def _read_from_cache(
        self,
        key: str,
    ) -> Optional[Dict[str, Any]]:
        try:
            cached = self.redis_client.get(key)

            if not cached:
                return None

            return json.loads(cached)

        except (
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ):
            self._delete_cache_key(key)
            return None

        except Exception:
            return None
    def _write_to_cache(self, key: str, data: Dict[str, Any]) -> None:
        try:
            self.redis_client.setex(key, self.cache_ttl_seconds, json.dumps(data))
        except Exception:
            pass

    def validate_variables(self, body: str, variables: List[str], title: Optional[str] = None) -> bool:
        try:
            _validate_jinja_variables(body, variables, title)
            return True
        except ValueError:
            return False

    def create(self, payload: PromptTemplateCreate) -> PromptTemplateResponse:
        # Check for conflicts
        existing = self.repo.list_templates(
            agent_type=payload.agent_type,
            channel=payload.channel,
            language=payload.language,
            status=payload.status,
            is_active=True
        )
        if any(
            item.version == payload.version
            for item in existing
        ):
            raise ConflictError("Active template with same attributes and version already exists.")

        try:
            model = self.repo.create(
        payload.model_dump(mode="json")
    )
            self.db.commit()
            self._invalidate_cache()
            return self._to_response(model)
        except TemplateConflictError:
            self.db.rollback()
            raise ConflictError("Active template with same attributes and version already exists.")
        except RepositoryError:
            self.db.rollback()
            raise RegistryServiceError("Failed to create template")

    def get(self, template_id: int) -> PromptTemplateResponse:
        cache_key = self._build_cache_key("prompt_get", id=template_id)
        cached = self._read_from_cache(cache_key)
        if cached:
            try:
                return PromptTemplateResponse.model_validate(
                    cached
                )
            except (
                ValidationError,
                ValueError,
                TypeError,
            ):
                self._delete_cache_key(
                    cache_key
                )

        try:
            model = self.repo.get_by_id(template_id)
            if not model:
                raise NotFoundError("Template not found")
            
            resp = self._to_response(model)
            if resp.is_active:
                self._write_to_cache(
                    cache_key,
                    resp.model_dump(mode="json"),
                )
            return resp
        except TemplateNotFoundError:
            raise NotFoundError("Template not found")
        except RepositoryError:
            raise RegistryServiceError("Database error")

    def update(self, template_id: int, payload: PromptTemplateUpdate) -> PromptTemplateResponse:
        try:
            model = self.repo.get_by_id(template_id)
            if not model:
                raise NotFoundError("Template not found")
            
            # Merge logic
            update_dict = payload.model_dump(
                exclude_unset=True,
                mode="json",
            )

            current_data = {
                "name": model.name,
                "agent_type": model.agent_type,
                "channel": "portal" if model.channel == "in_app" else model.channel,
                "language": model.locale,
                "status": model.type,
                "body": model.body_template,
                "title": model.title_template,
                "variables": model.variables,
                "is_active": model.is_active,
                "version": model.version
            }

            merged_data = {
                **current_data,
                    **update_dict,
            }

            PromptTemplateCreate.model_validate(
                merged_data
            )
            
            updated_model = self.repo.update(template_id, update_dict)
            self.db.commit()
                
            self._invalidate_cache()
            return self._to_response(updated_model)
        except TemplateNotFoundError:
            self.db.rollback()
            raise NotFoundError("Template not found during update")
        except TemplateConflictError:
            self.db.rollback()
            raise ConflictError("Active template with same attributes and version already exists.")
        except ValidationError:
            self.db.rollback()
            raise TemplateValidationServiceError(
                "Template validation failed."
            ) from None
        except RepositoryError:
            self.db.rollback()
            raise RegistryServiceError("Database error")

    def delete(self, template_id: int) -> None:
        try:
            self.repo.deactivate(template_id)
            self.db.commit()
            self._invalidate_cache()
        except TemplateNotFoundError:
            self.db.rollback()
            raise NotFoundError("Template not found")
        except RepositoryError:
            self.db.rollback()
            raise RegistryServiceError("Database error")

    def list(self, **kwargs) -> List[PromptTemplateResponse]:
        limit = kwargs.pop('limit', 100)
        offset = kwargs.pop('offset', 0)
        try:
            models = self.repo.list_templates(limit=limit, offset=offset, **kwargs)
            return [self._to_response(m) for m in models]
        except RepositoryError:
            raise RegistryServiceError("Database error")

    def find(self, agent_type: str, channel: str, language: str, status: str) -> PromptTemplateLookupResponse:
        cache_key = self._build_cache_key("prompt_find", agent_type=agent_type, channel=channel, language=language, status=status)
        cached = self._read_from_cache(cache_key)
        if cached:
            try:
                return PromptTemplateLookupResponse.model_validate(
                    cached
                )

            except (
                ValidationError,
                ValueError,
                TypeError,
            ):
                self._delete_cache_key(
                    cache_key
                )
        try:
            candidates = self.repo.find_active_candidates(agent_type, channel, language, status)
            
            # Order of precedence:
            # 1. Tenant: exact language + exact status
            # 2. Tenant: English + exact status
            # 3. Tenant: exact language + status="default"
            # 4. Tenant: English + status="default"
            # 5. Platform: exact language + exact status
            # 6. Platform: English + exact status
            # 7. Platform: exact language + status="default"
            # 8. Platform: English + status="default"
            
            match = None
            rules = [
                (self.tenant_id, language, status),
                (self.tenant_id, "en", status),
                (self.tenant_id, language, "default"),
                (self.tenant_id, "en", "default"),
                ("**platform**", language, status),
                ("**platform**", "en", status),
                ("**platform**", language, "default"),
                ("**platform**", "en", "default"),
            ]
            
            for t_id, lang, stat in rules:
                for c in candidates:
                    if c.tenant_id == t_id and c.locale == lang and c.type == stat:
                        match = c
                        break
                if match:
                    break
                    
            if match:
                resp = self._to_lookup_response(match)
                self._write_to_cache(cache_key, resp.model_dump(mode='json'))
                return resp
                
            # Built-in fallback
            fallback = PromptTemplateLookupResponse(
                id=None,
                name="Built-in Fallback",
                agent_type=AgentType(agent_type),
                channel=PromptChannel(channel),
                language=PromptLanguage("en"),
                status=status,
                body="You have a new update regarding your service.",
                variables=[],
                version=None,
                is_active=True,
                source="builtin_default"
            )
            return fallback
            
        except RepositoryError:
            raise RegistryServiceError("Database error")

    def _to_response(self, model: Any) -> PromptTemplateResponse:
        return PromptTemplateResponse(
            id=model.id,
            name=model.name,
            agent_type=AgentType(model.agent_type),
            channel=PromptChannel(model.channel),
            language=PromptLanguage(model.locale),
            status=model.type,
            body=model.body_template,
            title=model.title_template,
            variables=model.variables,
            version=model.version,
            is_active=model.is_active
        )
        
    def _to_lookup_response(self, model: Any) -> PromptTemplateLookupResponse:
        source = "platform" if model.tenant_id == "**platform**" else "tenant"
        return PromptTemplateLookupResponse(
            id=model.id,
            name=model.name,
            agent_type=AgentType(model.agent_type),
            channel=PromptChannel(model.channel),
            language=PromptLanguage(model.locale),
            status=model.type,
            body=model.body_template,
            title=model.title_template,
            variables=model.variables,
            version=model.version,
            is_active=model.is_active,
            source=source
        )
    def _delete_cache_key(
        self,
        key: str,
    ) -> None:
        try:
            self.redis_client.delete(key)
        except Exception:
            pass
