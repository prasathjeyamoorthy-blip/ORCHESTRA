import { Plus, Trash2, MessageSquare, PanelLeftClose, PanelLeftOpen } from 'lucide-react'
import { cn } from '@/lib/utils'

export function ChatSidebar({ sessions, activeId, onSelect, onNew, onDelete, collapsed, onToggle, newDisabled = false }) {
  return (
    <>
      {/* Floating toggle — only shown when sidebar is collapsed */}
      {collapsed && (
        <button
          onClick={onToggle}
          className="fixed top-3 left-3 z-40 p-2 rounded-lg text-white/30 hover:text-white/70 hover:bg-white/[0.06] transition-all"
          title="Open sidebar"
        >
          <PanelLeftOpen size={16} />
        </button>
      )}

      {/* Mobile backdrop — tap to close */}
      {!collapsed && (
        <div
          className="fixed inset-0 z-20 bg-black/50 md:hidden"
          onClick={onToggle}
          aria-hidden="true"
        />
      )}

      {/* Sidebar panel */}
      <div className={cn(
        'fixed top-0 left-0 h-full z-30 flex flex-col border-r border-white/[0.06] transition-all duration-200',
        'bg-[#0a0a12]',
        collapsed ? 'w-0 overflow-hidden opacity-0 pointer-events-none' : 'w-64 sm:w-60 opacity-100'
      )}>
        {/* Header — toggle lives here when open */}
        <div className="flex items-center justify-between px-3 pt-4 pb-3 mt-1">
          <div className="flex items-center gap-2">
            <button
              onClick={onToggle}
              className="p-1.5 rounded-lg text-white/30 hover:text-white/70 hover:bg-white/[0.06] transition-all"
              title="Close sidebar"
            >
              <PanelLeftClose size={15} />
            </button>
            <span className="text-white/40 text-[11px] font-semibold uppercase tracking-widest">Chats</span>
          </div>
          <button
            onClick={onNew}
            disabled={newDisabled}
            className={cn(
              "flex items-center gap-1.5 text-xs border px-2.5 py-1.5 rounded-lg transition-all",
              newDisabled
                ? "text-white/20 border-white/[0.04] cursor-not-allowed"
                : "text-white/50 hover:text-white border-white/[0.08] hover:border-white/20"
            )}
            title={newDisabled ? "Already on a new chat" : "New chat"}
          >
            <Plus size={12} /> New
          </button>
        </div>

        {/* Session list */}
        <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-0.5">
          {sessions.length === 0 && (
            <p className="text-white/20 text-xs px-2 py-3">No chats yet</p>
          )}
          {sessions.map(s => (
            <div
              key={s.id}
              onClick={() => { onSelect(s.id); if (window.innerWidth < 768) onToggle() }}
              className={cn(
                'group flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition-all',
                s.id === activeId
                  ? 'bg-white/[0.08] text-white'
                  : 'text-white/40 hover:text-white/70 hover:bg-white/[0.04]'
              )}
            >
              <MessageSquare size={13} className="flex-shrink-0 opacity-60" />
              <span className="flex-1 text-xs truncate">{s.title || 'New Chat'}</span>
              <button
                onClick={e => { e.stopPropagation(); onDelete(s.id) }}
                className="opacity-0 group-hover:opacity-100 text-white/30 hover:text-rose-400 transition-all p-0.5 rounded"
              >
                <Trash2 size={11} />
              </button>
            </div>
          ))}
        </div>
      </div>
    </>
  )
}
