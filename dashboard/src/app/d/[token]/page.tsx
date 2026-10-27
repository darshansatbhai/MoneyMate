import { supabaseServer } from '@/lib/supabaseServer'
import DashboardClient from '@/components/DashboardClient'
import Link from 'next/link'

export const instant = false

export default async function DashboardPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;

  if (token === 'demo') {
    return <DashboardClient userId="demo" userName="Darshan (Demo)" isDemo={true} />
  }

  try {
    const { data, error } = await supabaseServer
      .from('users')
      .select('*')
      .eq('dashboard_token', token)
      .single()

    if (error || !data) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-gray-100 p-4">
          <div className="text-center p-8 bg-white rounded-xl shadow-lg max-w-md w-full border border-gray-100">
            <div className="w-12 h-12 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center mx-auto mb-4 font-bold text-xl">
              📊
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">Token Not Found or Paused</h1>
            <p className="text-gray-600 text-sm mb-6">
              Could not find active user for this token, or Supabase project is paused.
            </p>
            <Link
              href="/d/demo"
              className="inline-block w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg text-sm transition-colors shadow-sm"
            >
              Explore Demo Dashboard 🚀
            </Link>
          </div>
        </div>
      )
    }

    return <DashboardClient userId={data.id} userName={data.name} />
  } catch {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-100 p-4">
        <div className="text-center p-8 bg-white rounded-xl shadow-lg max-w-md w-full border border-gray-100">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Database Unreachable</h1>
          <p className="text-gray-600 text-sm mb-6">
            Supabase server is not reachable. You can preview all features in Demo Mode.
          </p>
          <Link
            href="/d/demo"
            className="inline-block w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg text-sm transition-colors shadow-sm"
          >
            Launch Demo Dashboard 🚀
          </Link>
        </div>
      </div>
    )
  }
}
