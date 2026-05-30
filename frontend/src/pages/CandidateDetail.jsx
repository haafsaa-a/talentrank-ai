import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
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

// Guard: name may be missing or empty
function Avatar({ name, large }) {
  const safeName = name && name.trim() ? name : '?';
  const initials = safeName === '?'
    ? '?'
    : safeName.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase();
  const colors = ['from-blue-500 to-indigo-600', 'from-emerald-500 to-teal-600', 'from-violet-500 to-purple-600', 'from-rose-500 to-pink-600', 'from-amber-500 to-orange-600'];
  const color = colors[safeName.charCodeAt(0) % colors.length];
  const size = large ? 'w-16 h-16 text-xl rounded-2xl' : 'w-10 h-10 text-sm rounded-xl';
  return (
    <div className={`${size} bg-gradient-to-br ${color} flex items-center justify-center text-white font-bold shadow-lg flex-shrink-0`}>
      {initials}
    </div>
  );
}

// Reusable placeholder shown when a data section is unavailable
function UnavailablePlaceholder({ label }) {
  return (
    <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-slate-50 border border-dashed border-slate-200">
      <svg className="w-4 h-4 text-slate-300 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M12 2a10 10 0 100 20A10 10 0 0012 2z" />
      </svg>
      <span className="text-sm text-slate-400">{label}</span>
    </div>
  );
}

export default function CandidateDetail() {
  const { id } = useParams();
  const [candidate, setCandidate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetch = async () => {
      try {
        let data;
        try {
          data = (await axios.get(`https://talentrank-backend.onrender.com/api/candidates/${id}`)).data;
        } catch {
          const mock = (await axios.get('https://talentrank-backend.onrender.com/api/mock/candidates')).data;
          data = mock.find(c => c.id === id);
          if (!data) throw new Error('Not found');
        }
        setCandidate(data);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, [id]);

  if (loading) return (
    <div className="max-w-5xl mx-auto animate-pulse px-4 sm:px-0">
      <div className="h-5 bg-slate-200 rounded w-32 mb-8" />
      <div className="bg-white rounded-2xl border border-slate-100 h-96" />
    </div>
  );

  if (error || !candidate) return (
    <div className="text-center py-20 px-4">
      <div className="text-5xl mb-4">😕</div>
      <h2 className="text-xl font-bold text-[#0F172A]">Candidate not found</h2>
      <Link to="/dashboard" className="mt-6 inline-block text-sm text-blue-600 hover:text-blue-500">← Back to Dashboard</Link>
    </div>
  );

  const profile = candidate.profile || {};
  const skills = Array.isArray(profile.skills) ? profile.skills : [];
  const domains = Array.isArray(profile.domain_tags) ? profile.domain_tags : [];
  const projects = Array.isArray(profile.top_projects) ? profile.top_projects : [];
  const cvSkills = Array.isArray(profile.cv_skills) ? profile.cv_skills : [];
  const cvExperience = Array.isArray(profile.cv_experience) ? profile.cv_experience : [];
  const cvEducation = Array.isArray(profile.cv_education) ? profile.cv_education : [];

  // Missing data flags — used to show placeholders instead of empty sections
  const linkedinUnavailable = !candidate.linkedin_connected || profile.raw_linkedin_data === null;
  const githubUnavailable = !candidate.github_url || candidate.github_url.toLowerCase().trim() === 'none';
  const portfolioUnavailable = !candidate.portfolio_url || candidate.portfolio_url.toLowerCase().trim() === 'none';

  return (
    <div className="max-w-5xl mx-auto pb-16 px-4 sm:px-0">
      <Link to="/dashboard" className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-blue-600 transition-colors mb-8">
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
        Back to Dashboard
      </Link>

      {/* Profile header */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden mb-6">
        <div className="bg-gradient-to-r from-[#0F172A] to-[#1E293B] px-5 sm:px-8 py-6 sm:py-8">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 sm:gap-5">
            <Avatar name={candidate.name} large />
            <div className="flex-1 min-w-0">
              {/* Guard: name may be missing */}
              <h1 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight break-words">
                {candidate.name || 'Unknown Candidate'}
              </h1>
              <p className="text-slate-400 mt-1 text-sm break-all">
                {candidate.email || 'No email on record'}
              </p>
              {/* Guard: domains may be empty — show nothing rather than empty row */}
              {domains.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {domains.map(tag => (
                    <span key={tag} className="px-2.5 py-0.5 rounded-md text-xs font-semibold bg-white/10 text-white border border-white/20">
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
            {/* Guard: only show years if it's a valid non-zero number */}
            {profile.experience_years != null && profile.experience_years > 0 && (
              <div className="text-center flex-shrink-0">
                <div className="text-2xl font-extrabold text-white">{profile.experience_years}</div>
                <div className="text-xs text-slate-400">yrs exp</div>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main column */}
        <div className="lg:col-span-2 space-y-6">

          {/* Summary — always rendered, shows placeholder if missing */}
          <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 sm:p-8">
            <h2 className="text-lg font-bold text-[#0F172A] mb-4 flex items-center gap-2">
              <span className="w-6 h-6 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-xs flex-shrink-0">AI</span>
              Executive Summary
            </h2>
            {profile.summary ? (
              <p className="text-slate-600 leading-relaxed bg-slate-50 rounded-xl p-5 border border-slate-100 text-sm sm:text-base">
                {profile.summary}
              </p>
            ) : (
              <UnavailablePlaceholder label="No summary generated yet." />
            )}
          </div>

          {/* CV Information — always rendered with per-section placeholders */}
          <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 sm:p-8">
            <h2 className="text-lg font-bold text-[#0F172A] mb-6 flex items-center gap-2">
              <span className="w-6 h-6 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-white text-xs flex-shrink-0">CV</span>
              CV Information
            </h2>

            {/* Skills from CV */}
            <div className="mb-6">
              <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Skills from CV</h3>
              {cvSkills.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {cvSkills.map(skill => (
                    <span key={skill} className="px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                      {skill}
                    </span>
                  ))}
                </div>
              ) : (
                <UnavailablePlaceholder label="No CV skills available." />
              )}
            </div>

            {/* Work Experience */}
            <div className="mb-6">
              <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Work Experience</h3>
              {cvExperience.length > 0 ? (
                <div className="space-y-3">
                  {cvExperience.map((exp, idx) => (
                    <div key={idx} className="rounded-xl border border-slate-100 p-4 bg-slate-50">
                      {/* Guard: individual fields within experience may be missing */}
                      <p className="font-semibold text-[#0F172A] text-sm">{exp.role || 'Role not specified'}</p>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {exp.company || 'Company not specified'}{exp.duration ? ` · ${exp.duration}` : ''}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <UnavailablePlaceholder label="No work experience on record." />
              )}
            </div>

            {/* Education */}
            <div>
              <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Education</h3>
              {cvEducation.length > 0 ? (
                <div className="space-y-3">
                  {cvEducation.map((edu, idx) => (
                    <div key={idx} className="rounded-xl border border-slate-100 p-4 bg-slate-50">
                      {/* Guard: individual fields within education may be missing */}
                      <p className="font-semibold text-[#0F172A] text-sm">{edu.degree || 'Degree not specified'}</p>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {edu.institution || 'Institution not specified'}{edu.year ? ` · ${edu.year}` : ''}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <UnavailablePlaceholder label="No education data on record." />
              )}
            </div>
          </div>

          {/* Projects — always rendered, shows placeholder if empty */}
          <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 sm:p-8">
            <h2 className="text-lg font-bold text-[#0F172A] mb-5">Top Projects</h2>
            {projects.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {projects.map((proj, idx) => (
                  <div key={idx} className="rounded-xl border border-slate-100 p-4 sm:p-5 hover:border-slate-200 hover:shadow-md transition-all group">
                    <div className="flex justify-between items-start mb-2 gap-2">
                      <h3 className="font-bold text-[#0F172A] truncate group-hover:text-blue-600 transition-colors text-sm min-w-0">
                        {proj.name || 'Unnamed project'}
                      </h3>
                      {/* Guard: stars may be null or 0 */}
                      {proj.stars != null && (
                        <div className="flex items-center text-amber-500 shrink-0 gap-1">
                          <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                          </svg>
                          <span className="text-xs font-medium">{proj.stars}</span>
                        </div>
                      )}
                    </div>
                    <p className="text-xs text-slate-500 line-clamp-2">
                      {proj.description || 'No description available.'}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <UnavailablePlaceholder label="No significant projects detected." />
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">

          {/* Skills — always rendered, shows placeholder if empty */}
          <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 sm:p-6">
            <h2 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">Skills Profile</h2>
            {skills.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {skills.map(skill => (
                  <span key={skill} className="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200 hover:bg-blue-50 hover:text-blue-700 hover:border-blue-100 transition-colors cursor-default break-all">
                    {skill}
                  </span>
                ))}
              </div>
            ) : (
              <UnavailablePlaceholder label="No skills extracted." />
            )}
          </div>

          {/* External Links — always rendered with per-source placeholders */}
          <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 sm:p-6">
            <h2 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">External Links</h2>
            <ul className="space-y-3">

              {/* LinkedIn — shows 'Not available' placeholder when data missing */}
              {linkedinUnavailable ? (
                <li className="flex items-center gap-3 text-sm font-medium text-slate-400">
                  <div className="w-8 h-8 rounded-lg bg-slate-50 flex items-center justify-center flex-shrink-0">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                    </svg>
                  </div>
                  LinkedIn data unavailable
                </li>
              ) : (
                <li className="flex items-center gap-3 text-sm font-medium text-emerald-600">
                  <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center flex-shrink-0">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  LinkedIn Connected
                </li>
              )}

              {/* GitHub — shows 'Not available' placeholder when URL missing */}
              {githubUnavailable ? (
                <li className="flex items-center gap-3 text-sm font-medium text-slate-400">
                  <div className="w-8 h-8 rounded-lg bg-slate-50 flex items-center justify-center flex-shrink-0">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                    </svg>
                  </div>
                  GitHub not available
                </li>
              ) : (
                <li>
                  <a href={candidate.github_url.trim()} target="_blank" rel="noreferrer"
                    className="flex items-center gap-3 text-sm font-medium text-slate-600 hover:text-blue-600 transition-colors group">
                    <div className="w-8 h-8 rounded-lg bg-slate-50 flex items-center justify-center group-hover:bg-blue-50 transition-colors flex-shrink-0">
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                        <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
                      </svg>
                    </div>
                    GitHub Profile
                  </a>
                </li>
              )}

              {/* Portfolio — shows 'Not available' placeholder when URL missing */}
              {portfolioUnavailable ? (
                <li className="flex items-center gap-3 text-sm font-medium text-slate-400">
                  <div className="w-8 h-8 rounded-lg bg-slate-50 flex items-center justify-center flex-shrink-0">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                    </svg>
                  </div>
                  Portfolio not available
                </li>
              ) : (
                <li>
                  <a href={candidate.portfolio_url.trim()} target="_blank" rel="noreferrer"
                    className="flex items-center gap-3 text-sm font-medium text-slate-600 hover:text-blue-600 transition-colors group">
                    <div className="w-8 h-8 rounded-lg bg-slate-50 flex items-center justify-center group-hover:bg-blue-50 transition-colors flex-shrink-0">
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                      </svg>
                    </div>
                    Personal Portfolio
                  </a>
                </li>
              )}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
