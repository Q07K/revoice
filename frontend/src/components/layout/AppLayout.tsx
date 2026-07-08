import {
  AudioWaveform,
  LayoutDashboard,
  LibraryBig,
  Mic,
  Sparkles,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'

import { ThemeToggle } from '@/components/layout/ThemeToggle'
import { cn } from '@/lib/utils'

interface NavItem {
  to: string
  label: string
  icon: LucideIcon
}

const NAV_ITEMS: NavItem[] = [
  { to: '/', label: '대시보드', icon: LayoutDashboard },
  { to: '/voices', label: '보이스 모델', icon: Mic },
  { to: '/covers/new', label: '커버 만들기', icon: Sparkles },
  { to: '/library', label: '라이브러리', icon: LibraryBig },
]

export function AppLayout() {
  return (
    <div className="flex min-h-svh">
      <aside className="sticky top-0 flex h-svh w-56 flex-col border-r border-sidebar-border bg-sidebar px-3 py-5">
        <div className="mb-6 flex items-center gap-2 px-2">
          <span className="flex size-8 items-center justify-center rounded-xl bg-sidebar-primary text-sidebar-primary-foreground">
            <AudioWaveform className="size-4" />
          </span>
          <span className="text-lg font-bold tracking-tight text-sidebar-primary">
            Revoice
          </span>
        </div>
        <nav className="flex flex-col gap-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm text-sidebar-foreground/70 transition-colors',
                  'hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                  isActive &&
                    'bg-sidebar-accent font-semibold text-sidebar-accent-foreground shadow-sm',
                )
              }
            >
              <item.icon className="size-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto flex items-center justify-between px-2">
          <span className="text-xs text-muted-foreground">v0.1</span>
          <ThemeToggle />
        </div>
      </aside>
      <main className="min-w-0 flex-1 px-8 py-8">
        <div className="mx-auto flex max-w-4xl flex-col gap-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
