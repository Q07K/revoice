import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'

import { AppLayout } from '@/components/layout/AppLayout'
import { Toaster } from '@/components/ui/sonner'
import { CoverCreatePage } from '@/features/covers/CoverCreatePage'
import { LibraryPage } from '@/features/covers/LibraryPage'
import { StudioPage } from '@/features/covers/StudioPage'
import { DashboardPage } from '@/features/dashboard/DashboardPage'
import { SeparationPage } from '@/features/separations/SeparationPage'
import { VideoCreatePage } from '@/features/videos/VideoCreatePage'
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
      { path: '/separations', element: <SeparationPage /> },
      { path: '/covers/new', element: <CoverCreatePage /> },
      { path: '/library', element: <LibraryPage /> },
      { path: '/covers/:coverId/video', element: <VideoCreatePage /> },
    ],
  },
  // The studio is a full-screen workspace, outside the app chrome.
  { path: '/covers/:coverId/studio', element: <StudioPage /> },
])

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <Toaster position="top-center" />
    </QueryClientProvider>
  )
}
