import { Link } from 'react-router-dom';

export default function LinkedInCallback() {
  return (
    <div className="min-h-[70vh] flex flex-col justify-center items-center text-center">
      <div className="bg-white p-10 rounded-2xl shadow-xl border border-gray-100 max-w-md w-full">
        <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-green-100 mb-6">
          <svg className="h-8 w-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">You're all set!</h2>
        <p className="text-gray-600 mb-8 leading-relaxed">
          Your LinkedIn profile has been successfully connected. Our AI is now processing your complete profile. Our team will review your application shortly.
        </p>
        <Link to="/" className="text-sm font-medium text-blue-600 hover:text-blue-500">
          Return to home
        </Link>
      </div>
    </div>
  );
}
