import { useEffect, useState } from 'react';
import { getAgentEvents } from '../../api/agent';
import { Bot, Wrench, CheckCircle, AlertTriangle, ArrowRight, Settings, Play } from 'lucide-react';


interface AgentEventItem {
  id: string;
  event_type: string;
  tool_name?: string | null;
  input_summary?: string | null;
  result_summary?: string | null;
  status?: string | null;
  created_at: string;
}

interface AgentEventTimelineProps {
  tripId: string;
  refreshKey?: number;
}

export function AgentEventTimeline({ tripId, refreshKey = 0 }: AgentEventTimelineProps) {
  const [events, setEvents] = useState<AgentEventItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!tripId) return;
    setLoading(true);
    getAgentEvents(tripId)
      .then(res => setEvents(res.events))
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  }, [tripId, refreshKey]);

  if (loading) {
    return <div className="text-slate-400 animate-pulse text-xs font-medium py-4">Loading agent execution log...</div>;
  }

  if (events.length === 0) {
    return <div className="text-slate-400 text-xs py-4">No agent activity logged yet.</div>;
  }

  const sortedEvents = [...events].reverse();

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'tool_call': return <Wrench className="w-3.5 h-3.5 text-blue-600" />;
      case 'tool_result': return <CheckCircle className="w-3.5 h-3.5 text-blue-600" />;
      case 'decision': return <Bot className="w-3.5 h-3.5 text-blue-600" />;
      case 'replan_started': return <Play className="w-3.5 h-3.5 text-blue-600" />;
      case 'replan_completed': return <CheckCircle className="w-3.5 h-3.5 text-blue-600" />;
      case 'validation': return <AlertTriangle className="w-3.5 h-3.5 text-blue-600" />;
      case 'state_update': return <Settings className="w-3.5 h-3.5 text-blue-600" />;
      default: return <ArrowRight className="w-3.5 h-3.5 text-blue-600" />;
    }
  };

  return (
    <div className="space-y-3">
      {sortedEvents.map((evt, idx) => (
        <div key={evt.id} className="relative pl-6 pb-2">
          {idx !== sortedEvents.length - 1 && (
            <div className="absolute top-5 left-[11px] w-[2px] h-full bg-slate-200" />
          )}
          
          <div className="flex items-start">
            <div className="absolute left-0 mt-0.5 flex items-center justify-center w-6 h-6 rounded-full border border-blue-200 bg-blue-50 text-blue-600">
              {getEventIcon(evt.event_type)}
            </div>
            
            <div className="flex-1 p-3 ml-2 rounded-lg border border-slate-200 bg-slate-50/50 shadow-sm text-xs">
              <div className="flex justify-between items-start mb-1">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-slate-800 capitalize">
                    {evt.event_type.replace('_', ' ')}
                  </span>
                  {evt.tool_name && (
                    <span className="text-[10px] font-mono font-bold bg-blue-50 border border-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
                      {evt.tool_name}
                    </span>
                  )}
                </div>
                <span className="text-[10px] text-slate-400 font-mono">
                  {new Date(evt.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
              </div>
              
              <div className="mt-1 text-slate-600 space-y-1">
                {evt.input_summary && (
                  <div>
                    <span className="font-semibold text-[10px] text-slate-400 uppercase tracking-wider block">Input</span>
                    <p className="bg-white border border-slate-200 px-2 py-1 rounded text-slate-800">{evt.input_summary}</p>
                  </div>
                )}
                {evt.result_summary && (
                  <div>
                    {evt.input_summary && <span className="font-semibold text-[10px] text-slate-400 uppercase tracking-wider block mt-1">Result</span>}
                    <p className="bg-white border border-slate-200 px-2 py-1 rounded text-slate-800">
                      {evt.result_summary}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
