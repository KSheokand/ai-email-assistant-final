// app/page.tsx

const backend = process.env.NEXT_PUBLIC_BACKEND_URL!;

export default function Home() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900">
      <div className="w-full max-w-xl bg-slate-900/70 border border-slate-700 rounded-3xl shadow-2xl p-10 backdrop-blur-md">
        <div className="flex items-center gap-3 mb-6">
          <div className="h-10 w-10 rounded-2xl bg-indigo-500 flex items-center justify-center font-bold text-xl">
            AI
          </div>
          <div>
            <h1 className="text-2xl font-semibold">AI Email Assistant</h1>
            <p className="text-sm text-slate-400">
              Log in with Google to manage your inbox with AI.
            </p>
          </div>
        </div>

        {/* 👇 use a normal link instead of button + onClick */}
        <a
          href={`${backend}/auth/login`}
          className="w-full flex items-center justify-center gap-3 bg-white text-slate-900 py-3 rounded-2xl font-medium hover:bg-slate-100 transition"
        >
          <span className="text-lg">🔐</span>
          <span>Continue with Google</span>
        </a>
      </div>
    </main>
  );
}
