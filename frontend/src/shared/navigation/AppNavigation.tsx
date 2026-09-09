import { useQueryClient } from '@tanstack/react-query'
import {
  ChevronDown,
  LayoutDashboard,
  LogOut,
  Settings,
  ShieldCheck,
  ChartNoAxesCombined,
  GitBranch,
  type LucideIcon,
} from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'

import gitLogoImage from '@/assets/images/GIT_logo.webp'
import { AudioControls } from '@/shared/audio/AudioControls'
import { authApi } from '@/shared/auth/authApi'
import { useRank } from '@/shared/progress/rank'
import type { User } from '@/shared/auth/types'
import { useAuthStore } from '@/shared/auth/useAuth'
import { GitCoinIcon } from '@/shared/wallet/components/GitCoinIcon'
import { useWalletSummary } from '@/shared/wallet/hooks/useWallet'
import { usePlayerLoadout } from '@/shared/player-loadout/usePlayerLoadout'
import { ADMIN_ROUTES, HOME_ROUTE, PERFORMANCE_ROUTE, SHOP_ROUTE, isStoryMapRoute, storyPath } from '@/shared/navigation/routes'
import { cn } from '@/shared/utils/cn'
import { useFocusTrap } from '@/shared/utils/useFocusTrap'

type PrimaryNavItem = {
  to: string
  label: string
  Icon: LucideIcon
  match: (pathname: string) => boolean
}

const primaryNavItems: PrimaryNavItem[] = [
  {
    to: HOME_ROUTE,
    label: 'Dashboard',
    Icon: LayoutDashboard,
    match: (pathname) => pathname === '/' || pathname.startsWith(HOME_ROUTE),
  },
  {
    // Land on the default story map; in-page story controls handle switching.
    to: storyPath(),
    label: 'Modules',
    Icon: GitBranch,
    match: isStoryMapRoute,
  },
  {
    to: PERFORMANCE_ROUTE,
    label: 'Performance',
    Icon: ChartNoAxesCombined,
    match: (pathname) => pathname === PERFORMANCE_ROUTE,
  },
]

const adminNavItem: PrimaryNavItem = {
  to: ADMIN_ROUTES.dashboard,
  label: 'Admin',
  Icon: ShieldCheck,
  match: (pathname) => pathname.startsWith(ADMIN_ROUTES.dashboard),
}

function formatBalance(balance: number, isPending?: boolean) {
  return isPending ? '---' : balance.toLocaleString()
}

function getInitials(username: string) {
  return (username?.slice(0, 2) || '??').toUpperCase()
}

function useAppLogout() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const clearSession = useAuthStore((state) => state.clearSession)

  return useCallback(async () => {
    try {
      await authApi.logout()
    } finally {
      queryClient.clear()
      clearSession()
      navigate('/login')
    }
  }, [clearSession, navigate, queryClient])
}

type PrimaryNavProps = {
  includeAdmin?: boolean
  navClassName: string
  linkClassName: string
  activeClassName?: string
}

function PrimaryNav({
  includeAdmin = false,
  navClassName,
  linkClassName,
  activeClassName = 'is-active',
}: PrimaryNavProps) {
  const location = useLocation()
  const navItems = includeAdmin ? [...primaryNavItems, adminNavItem] : primaryNavItems

  return (
    <nav className={navClassName} aria-label="Primary">
      {navItems.map(({ to, label, Icon, match }) => {
        const matchesCurrentPath = match(location.pathname)

        return (
          <NavLink
            key={to}
            aria-current={matchesCurrentPath ? 'page' : undefined}
            className={({ isActive }) =>
              cn(linkClassName, (isActive || matchesCurrentPath) && activeClassName)
            }
            to={to}
          >
            <Icon aria-hidden="true" />
            <span>{label}</span>
          </NavLink>
        )
      })}
    </nav>
  )
}

function CurrentUserPrimaryNav(props: Omit<PrimaryNavProps, 'includeAdmin'>) {
  const user = useAuthStore((state) => state.user)

  return <PrimaryNav {...props} includeAdmin={Boolean(user?.is_staff)} />
}

function ProfileAvatar({
  initials,
  className,
  open,
  src,
}: {
  initials: string
  className: string
  open: boolean
  src?: string
}) {
  return (
    <span className={cn(className, open && 'is-open')} title={initials}>
      {src ? <img src={src} alt="" /> : <span className="app-profile-avatar-initials">{initials}</span>}
    </span>
  )
}

function DropdownItem({
  icon: Icon,
  label,
  danger = false,
  onClick,
}: {
  icon: LucideIcon
  label: string
  danger?: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      className={cn(
        'app-profile-menu-item',
        danger ? 'app-profile-menu-item--danger' : 'app-profile-menu-item--normal',
      )}
      onClick={onClick}
    >
      <Icon aria-hidden="true" />
      {label}
    </button>
  )
}

function ProfileDropdown({
  user,
  onLogout,
  onNavigate,
}: {
  user: User
  onLogout: () => void | Promise<void>
  onNavigate: (to: string) => void
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  const rank = useRank()
  const playerLoadout = usePlayerLoadout()
  const initials = getInitials(user.username)
  const displayName = user.username || 'Adventurer'
  const rankLabel = rank ? `Rank ${rank.tier.numeral}` : 'Rank --'
  const avatarSrc = playerLoadout.hasCompanion
    ? playerLoadout.companion.sprites.avatar?.src ??
      playerLoadout.companion.sprites.portrait?.src ??
      playerLoadout.companion.sprites.idle.src
    : undefined

  useEffect(() => {
    if (!open) return

    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }

    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [open])

  useFocusTrap(panelRef, open)

  return (
    <div ref={ref} className="app-profile">
      <button
        type="button"
        aria-label={`${open ? 'Close' : 'Open'} account menu for ${displayName}`}
        aria-expanded={open}
        aria-controls="app-profile-menu"
        className="app-profile-trigger"
        onClick={() => setOpen((value) => !value)}
      >
        <ProfileAvatar
          initials={initials}
          className="app-profile-avatar"
          open={open}
          src={avatarSrc}
        />
        <span className="app-profile-copy">
          <strong>{displayName}</strong>
          <span>{rankLabel}</span>
        </span>
        <ChevronDown className={cn(open && 'is-open')} aria-hidden="true" />
      </button>

      {open ? (
        <div ref={panelRef} id="app-profile-menu" className="dropdown-menu app-profile-menu">
          <div className="app-profile-menu-head">
            <div>
              <p>{displayName}</p>
              <span>{user.email}</span>
            </div>
          </div>

          <div className="app-profile-menu-list">
            <DropdownItem
              icon={Settings}
              label="Settings"
              onClick={() => {
                setOpen(false)
                onNavigate('/settings')
              }}
            />
            {user.is_staff ? (
              <DropdownItem
                icon={ShieldCheck}
                label="Admin console"
                onClick={() => {
                  setOpen(false)
                  onNavigate(ADMIN_ROUTES.dashboard)
                }}
              />
            ) : null}
          </div>

          <div className="app-profile-menu-list app-profile-menu-list--bordered">
            <DropdownItem
              icon={LogOut}
              label="Logout"
              danger
              onClick={() => {
                setOpen(false)
                void onLogout()
              }}
            />
          </div>
        </div>
      ) : null}
    </div>
  )
}

function AppWalletLink({ balance, isPending }: { balance: number; isPending?: boolean }) {
  return (
    <NavLink to={SHOP_ROUTE} className="app-wallet" aria-label="Open shop">
      <GitCoinIcon />
      <span>
        <strong>{formatBalance(balance, isPending)}</strong>
        <small>GitCoins</small>
      </span>
    </NavLink>
  )
}

function AppAccountCluster({ user }: { user: User | null }) {
  const navigate = useNavigate()
  const logout = useAppLogout()
  const wallet = useWalletSummary()
  const balance = wallet.data?.balance ?? 0

  return (
    <div className="app-account">
      <AudioControls className="app-audio-controls" buttonClassName="app-audio-control" />
      {user ? <AppWalletLink balance={balance} isPending={wallet.isPending} /> : null}
      {user ? <ProfileDropdown user={user} onLogout={logout} onNavigate={navigate} /> : null}
    </div>
  )
}

export function AppTopbar({ className }: { className?: string }) {
  const user = useAuthStore((state) => state.user)

  return (
    <header className={cn('app-topbar', className)}>
      <NavLink to="/home" aria-label="GIT it! home" className="app-brand">
        <img src={gitLogoImage} alt="" />
        <span>
          <strong>GIT it!</strong>
          <small>Level up your Git</small>
        </span>
      </NavLink>

      <CurrentUserPrimaryNav navClassName="app-nav" linkClassName="app-nav-link" />

      <AppAccountCluster user={user} />
    </header>
  )
}


export function AppMobileNav() {
  const user = useAuthStore((state) => state.user)

  return (
    <PrimaryNav
      includeAdmin={Boolean(user?.is_staff)}
      navClassName={cn('app-mobile-nav', user?.is_staff && 'has-admin')}
      linkClassName="app-mobile-nav-link"
      activeClassName="is-active"
    />
  )
}
