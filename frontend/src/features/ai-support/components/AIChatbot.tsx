import { useMutation } from '@tanstack/react-query'
import { BookOpen, Send, ShieldCheck, Sparkles, X } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { useLocation } from 'react-router-dom'

import { aiSupportApi } from '@/features/ai-support/api/aiSupportApi'
import type { AIChatRequest } from '@/features/ai-support/api/aiSupportApi'
import { aiPageContext, aiPageContextLabel } from '@/features/ai-support/utils/routeContext'
import { ApiError } from '@/shared/api/apiError'
import { useAuthStore } from '@/shared/auth/useAuth'
import type { SpriteDef } from '@/shared/cosmetics/types'
import { usePlayerLoadout } from '@/shared/player-loadout/usePlayerLoadout'
import { SpriteAnimator } from '@/shared/sprites/SpriteAnimator'
import type { SpriteAnimation } from '@/shared/sprites/types'

type HistoryMessage = { role: 'user' | 'assistant'; content: string }
type DisplayMessage = HistoryMessage & {
  id: number
  policyStatus?: 'allowed' | 'redirected'
  transient?: boolean
}

const WELCOME_MESSAGE: DisplayMessage = {
  id: 0,
  role: 'assistant',
  content:
    "Hi! I’m your Git learning companion. Ask me about branches, commits, merging, rebasing, HEAD, remotes, or another Git concept. I won’t reveal scenario answers, but I’ll help you reason through the ideas.",
}

function spriteAnimation(sprite: SpriteDef, name: string): SpriteAnimation {
  return {
    name,
    src: sprite.src,
    frameWidth: sprite.frameWidth,
    frameHeight: sprite.frameHeight,
    columns: sprite.columns,
    rows: sprite.rows,
    frameCount: sprite.frameCount,
    fps: sprite.fps,
    loop: sprite.loops,
    displayScale: sprite.displayScale,
  }
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 429) {
    return 'The assistant is receiving too many questions right now. Please wait a moment and try again.'
  }
  if (error instanceof ApiError && error.status === 503) {
    return 'The assistant is temporarily unavailable. Your question was not sent; please try again later.'
  }
  return 'I couldn’t reach the assistant. Check your connection and try again.'
}

export function AIChatbot() {
  const user = useAuthStore((state) => state.user)
  const { companion, companionSlug } = usePlayerLoadout()
  const location = useLocation()
  const context = aiPageContext(location.pathname)
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState('')
  const [messages, setMessages] = useState<DisplayMessage[]>([WELCOME_MESSAGE])
  const [history, setHistory] = useState<HistoryMessage[]>([])
  const nextId = useRef(1)
  const launcherRef = useRef<HTMLButtonElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const mutation = useMutation({ mutationFn: (payload: AIChatRequest) => aiSupportApi.chat(payload) })
  const reducedMotion =
    typeof document !== 'undefined' && document.documentElement.dataset.motion === 'reduced'
  const sprite = mutation.isPending ? companion.sprites.run : companion.sprites.idle
  const animation = useMemo(
    () => spriteAnimation(sprite, `${companionSlug}.${mutation.isPending ? 'thinking' : 'assistant-idle'}`),
    [companionSlug, mutation.isPending, sprite],
  )

  const close = useCallback(() => {
    setOpen(false)
    window.requestAnimationFrame(() => launcherRef.current?.focus())
  }, [])

  useEffect(() => {
    if (!open) return
    inputRef.current?.focus()
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        close()
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [close, open])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ block: 'nearest' })
  }, [messages, mutation.isPending, open])

  useEffect(() => {
    setMessages([WELCOME_MESSAGE])
    setHistory([])
    setDraft('')
    setOpen(false)
  }, [user?.id])

  if (!user || user.is_staff || !context) return null

  const send = async () => {
    const message = draft.trim()
    if (!message || mutation.isPending) return

    const userMessage: DisplayMessage = { id: nextId.current++, role: 'user', content: message }
    setMessages((current) => [...current, userMessage])
    setDraft('')

    const payload: AIChatRequest = {
      message,
      history: history.slice(-12),
      page_context: context,
    }

    try {
      const response = await mutation.mutateAsync(payload)
      const assistantMessage: DisplayMessage = {
        id: nextId.current++,
        role: 'assistant',
        content: response.reply,
        policyStatus: response.policy_status,
      }
      setMessages((current) => [...current, assistantMessage])
      setHistory((current) => [
        ...current,
        { role: 'user', content: message },
        { role: 'assistant', content: response.reply },
      ].slice(-12) as HistoryMessage[])
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          id: nextId.current++,
          role: 'assistant',
          content: errorMessage(error),
          transient: true,
        },
      ])
    }
  }

  return (
    <aside className="ai-chatbot" data-open={open || undefined}>
      {open ? (
        <section
          id="ai-chatbot-panel"
          className="ai-chatbot__panel"
          role="dialog"
          aria-modal="false"
          aria-labelledby="ai-chatbot-title"
        >
          <header className="ai-chatbot__header">
            <div className="ai-chatbot__portrait" aria-hidden="true">
              <SpriteAnimator
                animation={animation}
                scale={0.25}
                autoPlay={!reducedMotion}
                pixelated
                anchorToPixelBounds
                pixelAnchorFallback={{ bottomOffset: companion.metrics.foot_offset ?? 0 }}
              />
            </div>
            <div className="ai-chatbot__heading">
              <span className="ai-chatbot__eyebrow"><Sparkles size={12} /> Conceptual Git help</span>
              <h2 id="ai-chatbot-title">Ask {companion.label}</h2>
            </div>
            <span className="ai-chatbot__policy"><ShieldCheck size={12} /> No-answer policy</span>
            <button className="ai-chatbot__close" type="button" onClick={close} aria-label="Close Git assistant">
              <X size={17} />
            </button>
          </header>

          <div className="ai-chatbot__context">
            <BookOpen size={13} aria-hidden="true" /> Context: {aiPageContextLabel(context)}
          </div>

          <div className="ai-chatbot__messages app-scrollbar" aria-live="polite" aria-busy={mutation.isPending}>
            {messages.map((message) => (
              <div className={`ai-chatbot__message ai-chatbot__message--${message.role}`} key={message.id}>
                {message.role === 'assistant' ? <span className="ai-chatbot__speaker">AI</span> : null}
                <div
                  className="ai-chatbot__bubble"
                  data-policy={message.policyStatus}
                  data-transient={message.transient || undefined}
                >
                  {message.role === 'assistant'
                    ? <ReactMarkdown>{message.content}</ReactMarkdown>
                    : message.content}
                </div>
              </div>
            ))}
            {mutation.isPending ? (
              <div className="ai-chatbot__message ai-chatbot__message--assistant">
                <span className="ai-chatbot__speaker">AI</span>
                <div className="ai-chatbot__typing" aria-label="Assistant is thinking">
                  <i /><i /><i />
                </div>
              </div>
            ) : null}
            <div ref={messagesEndRef} />
          </div>

          <form
            className="ai-chatbot__composer"
            onSubmit={(event) => {
              event.preventDefault()
              void send()
            }}
          >
            <label className="sr-only" htmlFor="ai-chatbot-input">Ask a Git concept question</label>
            <textarea
              id="ai-chatbot-input"
              ref={inputRef}
              value={draft}
              maxLength={1000}
              rows={2}
              placeholder="Ask about a Git concept..."
              disabled={mutation.isPending}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault()
                  void send()
                }
              }}
            />
            <button type="submit" disabled={!draft.trim() || mutation.isPending} aria-label="Send question">
              <Send size={17} />
            </button>
          </form>
          <p className="ai-chatbot__footer">Concept guidance only · No scenario answers</p>
        </section>
      ) : null}

      <button
        ref={launcherRef}
        type="button"
        className="ai-chatbot__launcher"
        aria-label="Open Git learning assistant"
        aria-expanded={open}
        aria-controls="ai-chatbot-panel"
        onClick={() => setOpen(true)}
      >
        <span className="ai-chatbot__launcher-glow" aria-hidden="true" />
        <SpriteAnimator
          animation={animation}
          scale={0.25}
          autoPlay={!reducedMotion}
          pixelated
          anchorToPixelBounds
          pixelAnchorFallback={{ bottomOffset: companion.metrics.foot_offset ?? 0 }}
          aria-label={`${companion.label}, Git learning assistant`}
        />
        <span className="ai-chatbot__launcher-badge" aria-hidden="true"><Sparkles size={12} /></span>
      </button>
    </aside>
  )
}
