import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'

import { AppLayout } from '@/components/layout/AppLayout'
import { Toaster } from '@/components/ui/sonner'
import { CoverCreatePage } from '@/features/covers/CoverCreatePage'
import { LibraryPage } from '@/features/covers/LibraryPage'
import { DashboardPage } from '@/features/dashboard/DashboardPage'
import { VoiceDetailPage } from '@/features/voices/VoiceDetailPage'
import { VoicesPage } from '@/features/voices/VoicesPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
})

const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { path: '/', element: <DashboardPage /> },
      { path: '/voices', element: <VoicesPage /> },
      { path: '/voices/:voiceId', element: <VoiceDetailPage /> },
      { path: '/covers/new', element: <CoverCreatePage /> },
      { path: '/library', element: <LibraryPage /> },
    ],
  },
])

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <Toaster position="top-center" />
    </QueryClientProvider>
  )
}
