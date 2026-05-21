import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  ArrowUpDown,
  CheckCircle2,
  ChevronDown,
  User,
  X,
  SlidersHorizontal,
} from 'lucide-react';
import TopThreeHighlight, {
  RankedTechnician,
  MEDAL_CONFIG,
  MedalTier,
} from './TopThreeHighlight';
import { getScoreLevel, formatScore, ScoreBadge } from './ScoreDisplay';

export interface RankedTechTableProps {
  job: {
    id: number;
    customer_name: string;
    priority?: string;
    location?: string;
    issue_description?: string;
  };
  candidates: RankedTechnician[];
  selectedTechId?: number;
  onSelect: (techId: number) => void;
  onAssign?: (techId: number) => void;
  onClose: () => void;
}

type SortField = 'score' | 'distance' | 'skill' | 'workload';
type SortOrder = 'asc' | 'desc';

export default function RankedTechTable({
  job,
  candidates,
  selectedTechId,
  onSelect,
  onAssign,
  onClose,
}: RankedTechTableProps) {
  // Sort and Filter States
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');
  const [skillFilter, setSkillFilter] = useState('All');
  const [sortField, setSortField] = useState<SortField>('score');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');

  // Ensure overall descending order by score for ranking determination
  const rankedAll = useMemo(() => {
    return [...candidates].sort((a, b) => b.composite_score - a.composite_score);
  }, [candidates]);

  // Pinned Top 3 candidates
  const pinnedTop3 = useMemo(() => {
    return rankedAll.slice(0, 3);
  }, [rankedAll]);

  // The rest of the candidates (Rank 4+) which are subject to filter & sort
  const otherCandidates = useMemo(() => {
    return rankedAll.slice(3);
  }, [rankedAll]);

  // Extract unique skills for the filter dropdown
  const uniqueSkills = useMemo(() => {
    const skills = new Set(candidates.map((c) => c.technician_skill));
    return Array.from(skills);
  }, [candidates]);

  // Filtered & Sorted normal list
  const filteredAndSortedOthers = useMemo(() => {
    let result = [...otherCandidates];

    // Search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (c) =>
          c.technician_name.toLowerCase().includes(q) ||
          c.technician_skill.toLowerCase().includes(q)
      );
    }

    // Status filter
    if (statusFilter !== 'All') {
      result = result.filter(
        (c) => c.technician_status.toLowerCase() === statusFilter.toLowerCase()
      );
    }

    // Skill filter
    if (skillFilter !== 'All') {
      result = result.filter(
        (c) => c.technician_skill.toLowerCase() === skillFilter.toLowerCase()
      );
    }

    // Sort
    result.sort((a, b) => {
      let valA: number = 0;
      let valB: number = 0;

      if (sortField === 'score') {
        valA = a.composite_score;
        valB = b.composite_score;
      } else if (sortField === 'distance') {
        valA = a.distance_km;
        valB = b.distance_km;
      } else if (sortField === 'skill') {
        valA = a.skill_score;
        valB = b.skill_score;
      } else if (sortField === 'workload') {
        valA = a.workload_score;
        valB = b.workload_score;
      }

      if (sortOrder === 'asc') {
        return valA - valB;
      } else {
        return valB - valA;
      }
    });

    return result;
  }, [otherCandidates, searchQuery, statusFilter, skillFilter, sortField, sortOrder]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      // Distance and workload default to asc, score and skill default to desc
      setSortOrder(field === 'distance' || field === 'workload' ? 'asc' : 'desc');
    }
  };

  const getStatusColor = (status: string) => {
    const s = status.toLowerCase();
    if (s === 'available') return 'bg-emerald-100 text-emerald-700 border-emerald-200';
    if (s === 'busy') return 'bg-amber-100 text-amber-700 border-amber-200';
    return 'bg-slate-100 text-slate-500 border-slate-200';
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -16 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
      className="bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden"
      role="region"
      aria-label={`Technician Selection for Job ${job.id}`}
      data-testid="ranked-tech-selection-panel"
    >
      {/* ── Panel Header ── */}
      <div className="bg-gradient-to-r from-slate-50 to-slate-100 px-6 py-4 border-b border-slate-200 flex items-center justify-between">
        <div>
          <h2 className="text-base font-black text-slate-800 flex items-center gap-2">
            <span>Candidate Selection</span>
            <span className="text-xs px-2 py-0.5 rounded bg-slate-200 text-slate-600 font-bold">
              Job #{job.id}
            </span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Assigning technician for <strong className="text-slate-700">{job.customer_name}</strong>
            {job.location && ` (${job.location})`}
          </p>
        </div>
        <button
          onClick={onClose}
          aria-label="Close candidate selection panel"
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-200/60 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400"
          data-testid="panel-close-btn"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* ── Pinned Top 3 Cards ── */}
      {pinnedTop3.length > 0 && (
        <div className="p-6 bg-slate-50/50 border-b border-slate-200/60">
          <TopThreeHighlight
            technicians={pinnedTop3}
            jobId={job.id}
            jobLabel={`Job #${job.id}`}
            onSelect={onSelect}
            onClose={onClose}
          />
        </div>
      )}

      {/* ── Filter / Sort Toolbar ── */}
      <div className="px-6 py-4 border-b border-slate-200 bg-white flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
            <Search className="w-4 h-4" />
          </span>
          <input
            type="text"
            placeholder="Search technician by name or skill..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/25 focus:border-emerald-500 transition-all placeholder-slate-400"
            aria-label="Search technicians"
            data-testid="toolbar-search-input"
          />
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-wider">
            <SlidersHorizontal className="w-3.5 h-3.5" />
            <span>Filters:</span>
          </div>

          {/* Skill Filter */}
          <select
            value={skillFilter}
            onChange={(e) => setSkillFilter(e.target.value)}
            className="px-3 py-1.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/25 bg-white cursor-pointer"
            aria-label="Filter by skill"
            data-testid="toolbar-skill-filter"
          >
            <option value="All">All Skills</option>
            {uniqueSkills.map((skill) => (
              <option key={skill} value={skill}>
                {skill}
              </option>
            ))}
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/25 bg-white cursor-pointer"
            aria-label="Filter by status"
            data-testid="toolbar-status-filter"
          >
            <option value="All">All Statuses</option>
            <option value="Available">Available</option>
            <option value="Busy">Busy</option>
            <option value="Offline">Offline</option>
          </select>
        </div>
      </div>

      {/* ── Table Area ── */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse" role="table" aria-label="Technician candidate pool">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="px-6 py-3.5 text-[10.5px] font-black uppercase text-slate-400 tracking-wider">Rank</th>
              <th className="px-6 py-3.5 text-[10.5px] font-black uppercase text-slate-400 tracking-wider">Technician</th>
              <th className="px-6 py-3.5 text-[10.5px] font-black uppercase text-slate-400 tracking-wider">Status</th>
              <th
                onClick={() => handleSort('distance')}
                className="px-6 py-3.5 text-[10.5px] font-black uppercase text-slate-400 tracking-wider cursor-pointer hover:bg-slate-100/80 transition-colors"
                role="columnheader"
                aria-sort={sortField === 'distance' ? sortOrder : 'none'}
              >
                <div className="flex items-center gap-1.5">
                  Distance
                  <ArrowUpDown className="w-3.5 h-3.5" />
                </div>
              </th>
              <th
                onClick={() => handleSort('skill')}
                className="px-6 py-3.5 text-[10.5px] font-black uppercase text-slate-400 tracking-wider cursor-pointer hover:bg-slate-100/80 transition-colors"
                role="columnheader"
                aria-sort={sortField === 'skill' ? sortOrder : 'none'}
              >
                <div className="flex items-center gap-1.5">
                  Skill Match
                  <ArrowUpDown className="w-3.5 h-3.5" />
                </div>
              </th>
              <th
                onClick={() => handleSort('workload')}
                className="px-6 py-3.5 text-[10.5px] font-black uppercase text-slate-400 tracking-wider cursor-pointer hover:bg-slate-100/80 transition-colors"
                role="columnheader"
                aria-sort={sortField === 'workload' ? sortOrder : 'none'}
              >
                <div className="flex items-center gap-1.5">
                  Workload
                  <ArrowUpDown className="w-3.5 h-3.5" />
                </div>
              </th>
              <th
                onClick={() => handleSort('score')}
                className="px-6 py-3.5 text-[10.5px] font-black uppercase text-slate-400 tracking-wider cursor-pointer hover:bg-slate-100/80 transition-colors"
                role="columnheader"
                aria-sort={sortField === 'score' ? sortOrder : 'none'}
              >
                <div className="flex items-center gap-1.5">
                  Score
                  <ArrowUpDown className="w-3.5 h-3.5" />
                </div>
              </th>
              <th className="px-6 py-3.5 text-[10.5px] font-black uppercase text-slate-400 tracking-wider text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {/* 1. Pinned Top 3 Pinned Rows */}
            {pinnedTop3.map((tech, idx) => {
              const tier = (idx === 0 ? 'gold' : idx === 1 ? 'silver' : 'bronze') as MedalTier;
              const cfg = MEDAL_CONFIG[tier];
              const isSelected = selectedTechId === tech.technician_id;

              return (
                <tr
                  key={`pinned-${tech.technician_id}`}
                  className={[
                    'border-b border-slate-100 transition-colors',
                    isSelected ? 'bg-amber-50/40' : 'bg-gradient-to-r from-amber-50/20 to-transparent hover:bg-slate-50/60',
                  ].join(' ')}
                  data-testid={`table-pinned-row-${idx + 1}`}
                  role="row"
                  aria-label={`Pinned Rank ${idx + 1} recommended: ${tech.technician_name}`}
                >
                  {/* Rank */}
                  <td className="px-6 py-4 font-black text-slate-800">
                    <span
                      style={{ color: cfg.hex }}
                      className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-white border border-slate-200 text-xs shadow-sm font-black"
                    >
                      {idx + 1}
                    </span>
                  </td>
                  {/* Technician info */}
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div
                        style={{ background: `linear-gradient(135deg, ${cfg.hex}aa, ${cfg.hex})` }}
                        className="w-8 h-8 rounded-full flex items-center justify-center text-white font-extrabold text-xs shadow-sm"
                      >
                        {tech.technician_name.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <div className="text-sm font-bold text-slate-800 leading-tight">
                          {tech.technician_name}
                        </div>
                        <div className="text-[11px] text-slate-400 mt-0.5">
                          {tech.technician_skill}
                        </div>
                      </div>
                    </div>
                  </td>
                  {/* Status */}
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider border ${getStatusColor(tech.technician_status)}`}>
                      {tech.technician_status}
                    </span>
                  </td>
                  {/* Distance */}
                  <td className="px-6 py-4 font-bold text-slate-600 text-sm">{tech.distance_km.toFixed(1)} km</td>
                  {/* Skill match */}
                  <td className="px-6 py-4 font-bold text-slate-600 text-sm">{tech.skill_score.toFixed(0)}%</td>
                  {/* Workload */}
                  <td className="px-6 py-4 font-bold text-slate-600 text-sm">
                    {tech.active_jobs}/{tech.max_capacity}
                  </td>
                  {/* Score */}
                  <td className="px-6 py-4">
                    <ScoreBadge score={tech.composite_score} label="Score" />
                  </td>
                  {/* Select Actions */}
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => onSelect(tech.technician_id)}
                        className={[
                          'px-3 py-1.5 rounded-lg text-xs font-bold transition-all shadow-sm focus:outline-none focus:ring-2',
                          isSelected
                            ? 'bg-emerald-600 text-white hover:bg-emerald-700 focus:ring-emerald-500'
                            : 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-50 focus:ring-slate-300',
                        ].join(' ')}
                        aria-label={`Select ${tech.technician_name} for Job ${job.id}`}
                        data-testid={`table-pinned-select-${idx + 1}`}
                      >
                        {isSelected ? 'Selected' : 'Select'}
                      </button>
                      {onAssign && (
                        <button
                          onClick={() => onAssign(tech.technician_id)}
                          className="px-3 py-1.5 rounded-lg text-xs font-bold bg-emerald-100 text-emerald-800 hover:bg-emerald-200 focus:outline-none focus:ring-2 focus:ring-emerald-400 shadow-sm"
                          aria-label={`Assign ${tech.technician_name} immediately`}
                          data-testid={`table-pinned-assign-${idx + 1}`}
                        >
                          Assign
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}

            {/* Divider row */}
            {filteredAndSortedOthers.length > 0 && (
              <tr>
                <td colSpan={8} className="bg-slate-50/80 px-6 py-2 border-y border-slate-200/60">
                  <span className="text-[10px] font-black uppercase text-slate-400 tracking-wider">
                    Other Candidates (Filtered & Sorted)
                  </span>
                </td>
              </tr>
            )}

            {/* 2. Sorted and Filtered Others list */}
            {filteredAndSortedOthers.map((tech, idx) => {
              const overallRank = idx + 4;
              const isSelected = selectedTechId === tech.technician_id;

              return (
                <tr
                  key={`other-${tech.technician_id}`}
                  className={[
                    'border-b border-slate-100 transition-colors',
                    isSelected ? 'bg-emerald-50/40' : 'hover:bg-slate-50/40',
                  ].join(' ')}
                  data-testid={`table-other-row-${idx}`}
                  role="row"
                  aria-label={`Rank ${overallRank}: ${tech.technician_name}`}
                >
                  {/* Rank */}
                  <td className="px-6 py-4 font-semibold text-slate-400 text-sm">#{overallRank}</td>
                  {/* Technician info */}
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-slate-200 text-slate-600 font-extrabold text-xs flex items-center justify-center shadow-sm">
                        {tech.technician_name.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <div className="text-sm font-bold text-slate-700 leading-tight">
                          {tech.technician_name}
                        </div>
                        <div className="text-[11px] text-slate-400 mt-0.5">
                          {tech.technician_skill}
                        </div>
                      </div>
                    </div>
                  </td>
                  {/* Status */}
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider border ${getStatusColor(tech.technician_status)}`}>
                      {tech.technician_status}
                    </span>
                  </td>
                  {/* Distance */}
                  <td className="px-6 py-4 font-semibold text-slate-500 text-sm">{tech.distance_km.toFixed(1)} km</td>
                  {/* Skill match */}
                  <td className="px-6 py-4 font-semibold text-slate-500 text-sm">{tech.skill_score.toFixed(0)}%</td>
                  {/* Workload */}
                  <td className="px-6 py-4 font-semibold text-slate-500 text-sm">
                    {tech.active_jobs}/{tech.max_capacity}
                  </td>
                  {/* Score */}
                  <td className="px-6 py-4">
                    <ScoreBadge score={tech.composite_score} label="Score" />
                  </td>
                  {/* Select Actions */}
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => onSelect(tech.technician_id)}
                        className={[
                          'px-3 py-1.5 rounded-lg text-xs font-bold transition-all shadow-sm focus:outline-none focus:ring-2',
                          isSelected
                            ? 'bg-emerald-600 text-white hover:bg-emerald-700 focus:ring-emerald-500'
                            : 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-50 focus:ring-slate-300',
                        ].join(' ')}
                        aria-label={`Select ${tech.technician_name} for Job ${job.id}`}
                        data-testid={`table-other-select-${idx}`}
                      >
                        {isSelected ? 'Selected' : 'Select'}
                      </button>
                      {onAssign && (
                        <button
                          onClick={() => onAssign(tech.technician_id)}
                          className="px-3 py-1.5 rounded-lg text-xs font-bold bg-emerald-100 text-emerald-800 hover:bg-emerald-200 focus:outline-none focus:ring-2 focus:ring-emerald-400 shadow-sm"
                          aria-label={`Assign ${tech.technician_name} immediately`}
                          data-testid={`table-other-assign-${idx}`}
                        >
                          Assign
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}

            {/* Empty state for search/filters */}
            {filteredAndSortedOthers.length === 0 && (
              <tr>
                <td colSpan={8} className="px-6 py-10 text-center text-slate-400 text-sm">
                  No other candidates match the selected filters or search criteria.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* ── Table Footer ── */}
      <div className="bg-slate-50 px-6 py-3 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
        <span>Total Candidates: {candidates.length}</span>
        <span>Top 3 recommendations remain pinned to top. Sort & filters affect lower list.</span>
      </div>
    </motion.div>
  );
}
