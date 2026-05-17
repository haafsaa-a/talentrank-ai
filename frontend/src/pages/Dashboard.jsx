import { useState, useEffect } from 'react';
import axios from 'axios';
import CandidateCard from '../components/CandidateCard';
import FilterBar from '../components/FilterBar';

export default function Dashboard() {
  const [candidates, setCandidates] = useState([]);
  const [filteredCandidates, setFilteredCandidates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(null);
  const [stats, setStats] = useState({ total: 0, done: 0, pending: 0 });
  const [domains, setDomains] = useState([]);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [candResp, statsResp] = await Promise.allSettled([
          axios.get('http://localhost:8000/api/candidates'),
          axios.get('http://localhost:8000/api/stats'),
        ]);

        let data = [];
        if (candResp.status === 'fulfilled') {
          data = Array.isArray(candResp.value.data) ? candResp.value.data : [];
        } else {
          try {
            const mock = await axios.get('http://localhost:8000/api/mock/candidates');
            data = Array.isArray(mock.data) ? mock.data : [];
          } catch {
            setFetchError('Unable to load candidates. Please try again later.');
            setLoading(false);
            return;
          }
        }

        const statsData = statsResp.status === 'fulfilled'
          ? statsResp.value.data
          : {
              total: data.length,
              done: data.filter(c => c.profile).length,
              pending: data.filter(c => !c.profile).length,
            };

        setCandidates(data);
        setFilteredCandidates(data);
        setStats(statsData);

        const uniqueDomains = new Set();
        data.forEach(c => {
          if (Array.isArray(c.profile?.domain_tags)) {
            c.profile.domain_tags.forEach(d => uniqueDomains.add(d));
          }
        });
        setDomains(Array.from(uniqueDomains));

      } catch (e) {
        console.error(e);
        setFetchError('Something went wrong loading the dashboard.');
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
  }, []);

  const handleFilterChange = (filters) => {
    let result = candidates;
    if (filters.skill) {
      const lower = filters.skill.toLowerCase();
      result = result.filter(c =>
        Array.isArray(c.profile?.skills) &&
        c.profile.skills.some(s => s.toLowerCase().includes(lower))
      );
    }
    if (filters.domain) {
      result = result.filter(c =>
        Array.isArray(c.profile?.domain_tags) &&
        c.profile.domain_tags.includes(filters.domain)
      );
    }
    setFilteredCandidates(result);
  };

  const handleDelete = (deletedId) => {
    setCandidates(prev => prev.filter(c => c.id !== deletedId));
    setFilteredCandidates(prev => prev.filter(c => c.id !== deletedId));
    setStats(prev => ({
      ...prev,
      total: prev.total - 1,
      done: prev.done - 1,
    }));
  };

  return (
    <div>
      {/* Header */}
      <div className="mb-6 sm:mb-8">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-[#0F172A] tracking-tight">Candidates Dashboard</h1>
        <p className="mt-2 text-sm text-slate-500">AI-enriched candidate profiles, ready for review.</p>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4 mb-6 sm:mb-8">
        {[
          { label: 'Total Candidates', value: stats.total ?? 0, color: 'from-blue-500 to-indigo-600', shadow: 'shadow-blue-500/20' },
          { label: 'Profiles Ready',   value: stats.done  ?? 0, color: 'from-emerald-500 to-teal-600', shadow: 'shadow-emerald-500/20' },
          { label: 'Processing',       value: stats.pending ?? 0, color: 'from-amber-500 to-orange-600', shadow: 'shadow-amber-500/20' },
        ].map((s, i) => (
          <div key={i} className={`bg-gradient-to-br ${s.color} rounded-2xl p-4 sm:p-5 text-white shadow-lg ${s.shadow}`}>
            <div className="text-2xl sm:text-3xl font-extrabold">{s.value}</div>
            <div className="text-sm font-medium opacity-80 mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      <FilterBar domains={domains} onFilterChange={handleFilterChange} />

      {/* Fetch error state */}
      {fetchError && !loading && (
        <div className="text-center py-16 bg-white rounded-2xl border border-dashed border-red-200">
          <div className="text-4xl mb-4">⚠️</div>
          <h3 className="text-lg font-bold text-[#0F172A]">Failed to load candidates</h3>
          <p className="mt-1 text-sm text-slate-500">{fetchError}</p>
        </div>
      )}

      {/* Loading skeletons */}
      {loading && (
        <div className="grid grid-cols-1 gap-5 sm:gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="animate-pulse bg-white rounded-2xl border border-slate-100 p-6 h-64">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-slate-200 rounded-xl flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="h-4 bg-slate-200 rounded w-28 mb-2" />
                  <div className="h-3 bg-slate-100 rounded w-40" />
                </div>
              </div>
              <div className="h-3 bg-slate-100 rounded w-full mb-2" />
              <div className="h-3 bg-slate-100 rounded w-full mb-2" />
              <div className="h-3 bg-slate-100 rounded w-3/4" />
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && !fetchError && filteredCandidates.length === 0 && (
        <div className="text-center py-16 sm:py-20 bg-white rounded-2xl border border-dashed border-slate-200">
          <div className="text-5xl mb-4">🔍</div>
          <h3 className="text-lg font-bold text-[#0F172A]">No candidates found</h3>
          <p className="mt-1 text-sm text-slate-500">Try adjusting your filters or wait for new applications.</p>
        </div>
      )}

      {/* Candidate grid */}
      {!loading && !fetchError && filteredCandidates.length > 0 && (
        <div className="grid grid-cols-1 gap-5 sm:gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {filteredCandidates.map(candidate => (
            candidate && candidate.id
              ? <CandidateCard key={candidate.id} candidate={candidate} onDelete={handleDelete} />
              : null
          ))}
        </div>
      )}
    </div>
  );
}