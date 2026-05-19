/**
 * StatusBadge.test.js
 * In-browser test runner for StatusBadge (React Testing Library + Jest equivalent logic)
 * Because the project does not have Jest installed, this file runs directly
 * in the browser to assert behavior and verify rendering.
 *
 * Add route in App.jsx:
 *   import StatusBadgeTests from "./components/common/StatusBadge.test.jsx";
 *   {activeTab === "badge-test" && <StatusBadgeTests />}
 */

import React, { useState, useEffect } from "react";
import StatusBadge, { TECHNICIAN_STATUSES } from "./StatusBadge";
import { createRoot } from "react-dom/client";

// Minimal test framework
const tests = [];
function test(name, fn) {
  tests.push({ name, fn });
}

// Helpers
function renderComponent(ui) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  
  // Use synchronous rendering to assert immediately
  // Note: in a real RTL setup we'd use act(), here we just flush via microtask
  return new Promise(resolve => {
    root.render(<div id="test-root">{ui}</div>);
    setTimeout(() => {
      resolve({
        container,
        unmount: () => {
          root.unmount();
          document.body.removeChild(container);
        }
      });
    }, 0);
  });
}

// ── Tests definition ──
test("1. Renders all 7 statuses without crashing", async () => {
  const ui = (
    <div>
      {TECHNICIAN_STATUSES.map(s => <StatusBadge key={s} status={s} />)}
    </div>
  );
  const { container, unmount } = await renderComponent(ui);
  const badges = container.querySelectorAll(".sb-badge");
  if (badges.length !== 7) throw new Error(`Expected 7 badges, got ${badges.length}`);
  unmount();
});

test("2. Shows readable label text", async () => {
  const { container, unmount } = await renderComponent(<StatusBadge status="EN_ROUTE" />);
  const text = container.textContent;
  if (!text.includes("En Route")) throw new Error(`Expected text to include "En Route", got "${text}"`);
  unmount();
});

test("3. Applies correct color classes for each status", async () => {
  const { container, unmount } = await renderComponent(
    <div>
      <StatusBadge status="AVAILABLE" />
      <StatusBadge status="ON_SITE" />
    </div>
  );
  const badges = container.querySelectorAll(".sb-badge");
  if (!badges[0].classList.contains("sb-AVAILABLE")) throw new Error("Missing sb-AVAILABLE class");
  if (!badges[1].classList.contains("sb-ON_SITE")) throw new Error("Missing sb-ON_SITE class");
  unmount();
});

test("4. Supports sm, md, lg size variants", async () => {
  const { container, unmount } = await renderComponent(
    <div>
      <StatusBadge status="BUSY" size="sm" />
      <StatusBadge status="BUSY" size="md" />
      <StatusBadge status="BUSY" size="lg" />
    </div>
  );
  const badges = container.querySelectorAll(".sb-badge");
  if (!badges[0].classList.contains("sb-sm")) throw new Error("Missing sb-sm class");
  if (!badges[1].classList.contains("sb-md")) throw new Error("Missing sb-md class");
  if (!badges[2].classList.contains("sb-lg")) throw new Error("Missing sb-lg class");
  unmount();
});

test("5. Shows icon when showIcon=true (default)", async () => {
  const { container, unmount } = await renderComponent(<StatusBadge status="BUSY" />);
  const icon = container.querySelector(".sb-icon");
  if (!icon) throw new Error("Expected icon to be rendered");
  unmount();
});

test("6. Hides icon when showIcon=false", async () => {
  const { container, unmount } = await renderComponent(<StatusBadge status="BUSY" showIcon={false} />);
  const icon = container.querySelector(".sb-icon");
  if (icon) throw new Error("Expected icon to be hidden");
  unmount();
});

test("7. Applies pulse animation for EN_ROUTE by default", async () => {
  const { container, unmount } = await renderComponent(
    <div>
      <StatusBadge status="EN_ROUTE" />
      <StatusBadge status="AVAILABLE" />
    </div>
  );
  const badges = container.querySelectorAll(".sb-badge");
  if (!badges[0].classList.contains("sb-pulse")) throw new Error("EN_ROUTE should have pulse by default");
  if (badges[1].classList.contains("sb-pulse")) throw new Error("AVAILABLE should not pulse by default");
  unmount();
});

test("8. Applies custom pulse prop override", async () => {
  const { container, unmount } = await renderComponent(
    <div>
      <StatusBadge status="EN_ROUTE" pulse={false} />
      <StatusBadge status="AVAILABLE" pulse={true} />
    </div>
  );
  const badges = container.querySelectorAll(".sb-badge");
  if (badges[0].classList.contains("sb-pulse")) throw new Error("EN_ROUTE pulse should be overridden to false");
  if (!badges[1].classList.contains("sb-pulse")) throw new Error("AVAILABLE pulse should be overridden to true");
  unmount();
});

test("9. Has correct aria-label (role=status)", async () => {
  const { container, unmount } = await renderComponent(<StatusBadge status="AVAILABLE" />);
  const badge = container.querySelector(".sb-badge");
  const role = badge.getAttribute("role");
  const ariaLabel = badge.getAttribute("aria-label");
  if (role !== "status") throw new Error(`Expected role="status", got "${role}"`);
  if (!ariaLabel.includes("Available")) throw new Error(`Expected aria-label to contain "Available", got "${ariaLabel}"`);
  unmount();
});

test("10. Supports custom className", async () => {
  const { container, unmount } = await renderComponent(<StatusBadge status="BUSY" className="my-test-class" />);
  const badge = container.querySelector(".sb-badge");
  if (!badge.classList.contains("my-test-class")) throw new Error("Missing custom class");
  unmount();
});

// ── Runner component ──
export default function StatusBadgeTests() {
  const [results, setResults] = useState([]);
  const [running, setRunning] = useState(true);

  useEffect(() => {
    let mounted = true;
    
    async function runTests() {
      const res = [];
      for (const t of tests) {
        try {
          await t.fn();
          res.push({ name: t.name, status: "PASS", error: null });
        } catch (e) {
          res.push({ name: t.name, status: "FAIL", error: e.message });
        }
      }
      if (mounted) {
        setResults(res);
        setRunning(false);
      }
    }
    
    runTests();
    return () => { mounted = false; };
  }, []);

  return (
    <div style={{ padding: "40px", fontFamily: "'Inter', sans-serif", background: "#EEF4F1", minHeight: "100vh" }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, color: "#2F4F3E", marginBottom: 8 }}>StatusBadge — Test Runner</h1>
      <p style={{ color: "#6B7280", marginBottom: 32 }}>Executing isolated unit tests in-browser (RTL equivalent)</p>
      
      {running ? (
        <div style={{ fontSize: 14, color: "#2F4F3E" }}>Running tests...</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {results.map((r, i) => (
            <div key={i} style={{
              background: "#FFFFFF",
              border: `1px solid ${r.status === "PASS" ? "#B5D9C4" : "#FECACA"}`,
              borderRadius: 8,
              padding: "16px 20px",
              display: "flex",
              alignItems: "flex-start",
              gap: 16,
              boxShadow: "0 1px 3px rgba(0,0,0,.05)"
            }}>
              <div style={{ 
                background: r.status === "PASS" ? "#DDEEE5" : "#FEE2E2", 
                color: r.status === "PASS" ? "#1D6B3E" : "#991B1B",
                fontWeight: 700,
                fontSize: 12,
                padding: "4px 10px",
                borderRadius: 4
              }}>
                {r.status}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, color: "#1F2933", fontSize: 14, marginBottom: r.error ? 6 : 0 }}>
                  {r.name}
                </div>
                {r.error && (
                  <div style={{ color: "#991B1B", fontSize: 13, fontFamily: "monospace", background: "#FDF2F2", padding: "8px 12px", borderRadius: 4 }}>
                    {r.error}
                  </div>
                )}
              </div>
            </div>
          ))}
          
          <div style={{ marginTop: 24, padding: "16px 20px", background: "#FFFFFF", borderRadius: 8, border: "1px solid #E3ECE7", display: "inline-block" }}>
            <span style={{ fontWeight: 700, marginRight: 16 }}>Summary:</span>
            <span style={{ color: "#1D6B3E", fontWeight: 600, marginRight: 16 }}>{results.filter(r => r.status === "PASS").length} passed</span>
            <span style={{ color: "#991B1B", fontWeight: 600 }}>{results.filter(r => r.status === "FAIL").length} failed</span>
          </div>
        </div>
      )}
    </div>
  );
}
