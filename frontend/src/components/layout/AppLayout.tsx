import {
  AudioWaveform,
  Home,
  LibraryBig,
  Mic,
  Scissors,
  Sparkles,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'

import { ThemeToggle } from '@/components/layout/ThemeToggle'
import { CoverCompletionToaster } from '@/features/covers/CoverCompletionToaster'
import { cn } from '@/lib/utils'

interface NavItem {
  to: string
  label: string
  icon: LucideIcon
}

const MAIN_ITEMS: NavItem[] = [
  { to: '/', label: '홈', icon: Home },
  { to: '/library', label: '라이브러리', icon: LibraryBig },
]

const TOOL_ITEMS: NavItem[] = [
  { to: '/voices', label: '보이스 모델', icon: Mic },
  { to: '/separations', label: '반주 제거', icon: Scissors },
]

function NavItemLink({ item }: { item: NavItem }) {
  return (
    <NavLink
      to={item.to}
      end={item.to === '/'}
      className={({ isActive }) =>
        cn(
          'flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-medium text-sidebar-foreground/65 transition-colors',
          'hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
          isActive && 'bg-sidebar-accent font-semibold text-sidebar-accent-foreground shadow-sm',
        )
      }
    >
      <item.icon className="size-4" />
      {item.label}
    </NavLink>
  )
}

export function AppLayout() {
  return (
    <div className="flex min-h-svh">
      <aside className="sticky top-0 flex h-svh w-60 flex-col border-r border-sidebar-border bg-sidebar px-4 py-6">
        <div className="mb-7 flex items-center gap-2.5 px-1">
          <span className="flex size-9 items-center justify-center rounded-xl bg-sidebar-primary text-sidebar-primary-foreground">
            <AudioWaveform className="size-4.5" />
          </span>
          <span className="text-lg font-bold tracking-tight">Revoice</span>
        </div>

        <NavLink
          to="/covers/new"
          className={({ isActive }) =>
            cn(
              'mb-6 flex items-center justify-center gap-2 rounded-xl px-3 py-2.5 text-sm font-semibold shadow-sm transition-all',
              isActive
                ? 'bg-sidebar-primary text-sidebar-primary-foreground'
                : 'bg-sidebar-primary/90 text-sidebar-primary-foreground hover:bg-sidebar-primary',
            )
          }
        >
          <Sparkles className="size-4" />
          커버 만들기
        </NavLink>

        <nav className="flex flex-col gap-6">
          <div className="flex flex-col gap-1">
            {MAIN_ITEMS.map((item) => (
              <NavItemLink key={item.to} item={item} />
            ))}
          </div>
          <div className="flex flex-col gap-1">
            <span className="px-3 pb-1 text-xs font-medium text-sidebar-foreground/40">
              도구
            </span>
            {TOOL_ITEMS.map((item) => (
              <NavItemLink key={item.to} item={item} />
            ))}
          </div>
        </nav>

        <div className="mt-auto flex items-center justify-between px-1">
          <span className="text-xs text-muted-foreground">v0.1</span>
          <ThemeToggle />
        </div>
      </aside>
      <main className="min-w-0 flex-1 px-10 py-8">
        <div className="mx-auto flex max-w-5xl flex-col gap-8">
          <Outlet />
        </div>
      </main>
      <CoverCompletionToaster />
    </div>
  )
}
