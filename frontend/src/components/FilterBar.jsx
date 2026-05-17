import { useState } from 'react';

export default function FilterBar({ domains, onFilterChange }) {
  const [skill, setSkill] = useState('');
  const [domain, setDomain] = useState('');

  const handleApply = () => onFilterChange({ skill, domain });
  const handleClear = () => {
    setSkill(''); setDomain('');
    onFilterChange({ skill: '', domain: '' });
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 mb-6">
      <div className="flex flex-col sm:flex-row gap-4 items-end justify-between">
        <div className="flex flex-col sm:flex-row gap-4 w-full sm:w-auto">
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Search Skill</label>
            <input
              type="text"
              className="block w-full sm:w-48 rounded-xl border border-slate-200 px-3 py-2 text-sm text-[#0F172A] placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              placeholder="e.g. React"
              value={skill}
              onChange={(e) => setSkill(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleApply()}
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Domain</label>
            <select
              className="block w-full sm:w-48 rounded-xl border border-slate-200 px-3 py-2 text-sm text-[#0F172A] focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
            >
              <option value="">All Domains</option>
              {domains.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
        </div>
        <div className="flex gap-2 w-full sm:w-auto">
          <button onClick={handleClear}
            className="flex-1 sm:flex-none px-4 py-2 rounded-xl text-sm font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 transition-colors">
            Clear
          </button>
          <button onClick={handleApply}
            className="flex-1 sm:flex-none px-5 py-2 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-400 hover:to-indigo-500 transition-all shadow-lg shadow-blue-500/20">
            Apply Filters
          </button>
        </div>
      </div>
    </div>
  );
}
