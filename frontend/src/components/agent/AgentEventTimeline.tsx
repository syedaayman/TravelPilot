import { useEffect, useState } from 'react';
import { getAgentEvents } from '../../api/agent';
import { Bot, Wrench, CheckCircle, AlertTriangle, ArrowRight, Settings, Play } from 'lucide-react';
import { Badge } from '../common/Badge';

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
  refreshKey?: number; // pass a number to force re-fetch
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
    return <div className="text-gray-500 animate-pulse text-sm py-4">Loading agent events...</div>;
  }

  if (events.length === 0) {
    return <div className="text-gray-500 text-sm py-4">No agent activity yet.</div>;
  }

  // Reverse to show newest on top
  const sortedEvents = [...events].reverse();

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'tool_call': return <Wrench className="w-4 h-4" />;
      case 'tool_result': return <CheckCircle className="w-4 h-4" />;
      case 'decision': return <Bot className="w-4 h-4" />;
      case 'replan_started': return <Play className="w-4 h-4" />;
      case 'replan_completed': return <CheckCircle className="w-4 h-4" />;
      case 'validation': return <AlertTriangle className="w-4 h-4" />;
      case 'state_update': return <Settings className="w-4 h-4" />;
      default: return <ArrowRight className="w-4 h-4" />;
    }
  };

  const getEventColor = (type: string) => {
    switch (type) {
      case 'tool_call': return 'bg-blue-100 text-blue-700 border-blue-200';
      case 'tool_result': return 'bg-green-100 text-green-700 border-green-200';
      case 'decision': return 'bg-purple-100 text-purple-700 border-purple-200';
      case 'replan_started': return 'bg-yellow-100 text-yellow-700 border-yellow-200';
      case 'replan_completed': return 'bg-teal-100 text-teal-700 border-teal-200';
      case 'validation': return 'bg-orange-100 text-orange-700 border-orange-200';
      case 'state_update': return 'bg-gray-100 text-gray-700 border-gray-200';
      default: return 'bg-gray-50 text-gray-600 border-gray-200';
    }
  };

  return (
    <div className="space-y-4">
      {sortedEvents.map((evt, idx) => (
        <div key={evt.id} className="relative pl-6 pb-4">
          {/* Vertical line connector */}
          {idx !== sortedEvents.length - 1 && (
            <div className="absolute top-6 left-[11px] w-[2px] h-full bg-gray-200" />
          )}
          
          <div className="flex items-start">
            <div className={`absolute left-0 mt-1 flex items-center justify-center w-6 h-6 rounded-full border-2 bg-white ${getEventColor(evt.event_type).replace('bg-', 'border-').split(' ')[2]}`}>
              <div className={getEventColor(evt.event_type).split(' ')[1]}>
                {getEventIcon(evt.event_type)}
              </div>
            </div>
            
            <div className={`flex-1 p-3 ml-2 rounded-lg border ${getEventColor(evt.event_type)} shadow-sm`}>
              <div className="flex justify-between items-start mb-1">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className={`capitalize text-xs font-semibold bg-white/50 border-none`}>
                    {evt.event_type.replace('_', ' ')}
                  </Badge>
                  {evt.tool_name && (
                    <span className="text-xs font-mono font-bold bg-white/60 px-1.5 py-0.5 rounded">
                      {evt.tool_name}
                    </span>
                  )}
                </div>
                <span className="text-[10px] text-gray-500 font-medium">
                  {new Date(evt.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
              </div>
              
              <div className="mt-2 text-sm leading-relaxed">
                {evt.input_summary && (
                  <div className="mb-1">
                    <span className="font-semibold text-xs opacity-75 uppercase tracking-wider block mb-0.5">Input</span>
                    <p className="bg-white/50 px-2 py-1.5 rounded">{evt.input_summary}</p>
                  </div>
                )}
                {evt.result_summary && (
                  <div>
                    {evt.input_summary && <span className="font-semibold text-xs opacity-75 uppercase tracking-wider block mb-0.5 mt-2">Result</span>}
                    <p className={`px-2 py-1.5 rounded ${evt.input_summary ? 'bg-white/50' : ''}`}>
                      {evt.result_summary}
                    </p>
                  </div>
                )}
                {!evt.input_summary && !evt.result_summary && (
                   <p className="italic opacity-75 text-xs">Event recorded.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
