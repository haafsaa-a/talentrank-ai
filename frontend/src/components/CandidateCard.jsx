import { Link } from 'react-router-dom';
import axios from 'axios';

const domainColors = {
  Frontend: 'bg-blue-50 text-blue-700 border-blue-100',
  Backend: 'bg-emerald-50 text-emerald-700 border-emerald-100',
  Fullstack: 'bg-violet-50 text-violet-700 border-violet-100',
  'ML/AI': 'bg-rose-50 text-rose-700 border-rose-100',
  DevOps: 'bg-orange-50 text-orange-700 border-orange-100',
  Mobile: 'bg-cyan-50 text-cyan-700 border-cyan-100',
  Data: 'bg-amber-50 text-amber-700 border-amber-100',
  Design: 'bg-pink-50 text-pink-700 border-pink-100',
};

function Avatar({ name }) {
  const safeName = name && name.trim() ? name : '?';
  const initials = safeName === '?'
    ? '?'
    : safeName.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase();
  const colors = ['from-blue-500 to-indigo-600', 'from-emerald-500 to-teal-600', 'from-violet-500 to-purple-600', 'from-rose-500 to-pink-600', 'from-amber-500 to-orange-600'];
  const color = colors[safeName.charCodeAt(0) % colors.length];
  return (
    <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${color} flex items-center justify-center text-white text-sm font-bold shadow-sm flex-shrink-0`}>
      {initials}
    </div>
  );
}

export default function CandidateCard({ candidate, onDelete }) {
  if (!candidate) return null;

  const profile = candidate.profile || {};
  const skills = Array.isArray(profile.skills) ? profile.skills : [];
  const domains = Array.isArray(profile.domain_tags) ? profile.domain_tags : [];
  const hasProfile = !!candidate.profile;
  const linkedinUnavailable = hasProfile && !candidate.linkedin_connected && profile.raw_linkedin_data === null;

  const handleDelete = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!window.confirm(`Delete ${candidate.name || 'this candidate'}?`)) return;
    try {
      await axios.delete(`https://talentrank-backend.onrender.com/api/candidates/${candidate.id}`);
      onDelete(candidate.id);
    } catch (err) {
      alert('Failed to delete candidate.');
    }
  };

  return (
    <Link to={`/candidate/${candidate.id}`} className="block h-full group">
      <div className="bg-white rounded-2xl border border-slate-100 p-5 sm:p-6 h-full flex flex-col hover:shadow-xl hover:shadow-slate-200/60 hover:-translate-y-1 transition-all duration-300">

        {/* Header */}
        <div className="flex items-start gap-3 mb-4">
          <Avatar name={candidate.name} />
          <div className="min-w-0 flex-1">
            <h3 className="text-base font-bold text-[#0F172A] truncate group-hover:text-blue-600 transition-colors">
              {candidate.name || 'Unknown Candidate'}
            </h3>
            <p className="text-xs text-slate-400 truncate">
              {candidate.email || 'No email provided'}
            </p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            {hasProfile && (
              <span className="w-2 h-2 rounded-full bg-emerald-400 mt-1.5" title="Profile ready" />
            )}
            <button
              onClick={handleDelete}
              className="mt-0.5 p-1 rounded-lg text-slate-300 hover:text-red-500 hover:bg-red-50 transition-colors"
              title="Delete candidate"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>

        {/* LinkedIn unavailable badge */}
        {linkedinUnavailable && (
          <div className="mb-3 flex items-center gap-1.5 text-xs text-slate-400">
            <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M12 2a10 10 0 100 20A10 10 0 0012 2z" />
            </svg>
            LinkedIn data unavailable
          </div>
        )}

        {/* Domain tags */}
        {domains.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-1.5">
            {domains.map(tag => (
              <span
                key={tag}
                className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${domainColors[tag] || 'bg-slate-50 text-slate-600 border-slate-100'}`}
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* Summary */}
        <p className="text-sm text-slate-500 line-clamp-3 flex-grow leading-relaxed mb-4">
          {profile.summary
            ? profile.summary
            : hasProfile
              ? 'No summary generated.'
              : 'Profile is still being processed by AI...'}
        </p>

        {/* Skills */}
        {skills.length > 0 && (
          <div className="mt-auto pt-4 border-t border-slate-50">
            <div className="flex flex-wrap gap-1.5">
              {skills.slice(0, 3).map(skill => (
                <span key={skill} className="px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-100 text-slate-600 break-all">
                  {skill}
                </span>
              ))}
              {skills.length > 3 && (
                <span className="px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-50 text-slate-400">
                  +{skills.length - 3} more
                </span>
              )}
            </div>
          </div>
        )}

        {/* Processing state */}
        {!hasProfile && (
          <div className="mt-auto pt-4 border-t border-slate-50 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse flex-shrink-0" />
            <span className="text-xs text-slate-400">Processing...</span>
          </div>
        )}
      </div>
    </Link>
  );
}
