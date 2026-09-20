import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getTrip } from '../api/trips';
import type { TripDetailResponse } from '../types';
import { TripHealthCards } from '../components/dashboard/TripHealthCards';
import { DayItinerary } from '../components/itinerary/DayItinerary';
import { Button } from '../components/common/Button';
import { applyReplan, rejectReplan } from '../api/disruptions';
import { applySimulation, rejectSimulation } from '../api/simulations';
import { Card, CardContent, CardHeader, CardTitle } from '../components/common/Card';
import { Bot, Activity } from 'lucide-react';

import { AgentChatDrawer } from '../components/agent/AgentChatDrawer';
import { AgentEventTimeline } from '../components/agent/AgentEventTimeline';
import { DisruptionPanel } from '../components/disruption/DisruptionPanel';
import { SimulationPanel } from '../components/simulation/SimulationPanel';
import { ProposalReviewModal } from '../components/common/ProposalReviewModal';

export default function TripDashboardPage() {
  const { tripId } = useParams();
  const [trip, setTrip] = useState<TripDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Refresh Keys to trigger component updates
  const [refreshKey, setRefreshKey] = useState(0);

  // Agent Drawer State
  const [isAgentDrawerOpen, setIsAgentDrawerOpen] = useState(false);

  // Proposal States
  const [proposal, setProposal] = useState<any>(null);
  const [proposalType, setProposalType] = useState<'replan' | 'simulation' | null>(null);

  const fetchTrip = () => {
    if (!tripId) return;
    setLoading(true);
    getTrip(tripId)
      .then(t => {
        setTrip(t);
        setRefreshKey(prev => prev + 1); // refresh timeline events
      })
      .catch((err) => setError(err.message || 'Failed to load trip'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchTrip();
  }, [tripId]);

  const handleProposalReceived = (prop: any, type: 'replan' | 'simulation') => {
    setProposal(prop);
    setProposalType(type);
  };

  const handleApplyProposal = async (id: string, type: 'replan' | 'simulation') => {
    try {
      if (type === 'replan') await applyReplan(id);
      else await applySimulation(id);
      
      setProposal(null);
      setProposalType(null);
      fetchTrip();
    } catch (err: any) {
      if (err.status === 409) {
        setProposal(null);
        setProposalType(null);
        alert('Your trip changed while this proposal was open. The proposed changes are no longer based on the latest itinerary. Please refresh your trip.');
      } else {
        alert(err.message);
      }
    }
  };

  const handleRejectProposal = async (id: string, type: 'replan' | 'simulation') => {
    try {
      if (type === 'replan') await rejectReplan(id);
      else await rejectSimulation(id);
      
      setProposal(null);
      setProposalType(null);
    } catch (err: any) {
      alert(err.message);
    }
  };

  if (loading && !trip) return <div className="p-12 text-center text-gray-500 animate-pulse">Loading dashboard...</div>;
  if (error || !trip) return <div className="p-12 text-center text-red-500 bg-red-50 rounded-lg m-8">{error || 'Trip not found'}</div>;

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 relative">
      <div className="mb-8 flex justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
        <div>
          <h2 className="text-3xl font-bold text-gray-900 tracking-tight">{trip.title}</h2>
          <p className="text-gray-500 mt-2 font-medium flex items-center gap-2">
            {trip.start_date} to {trip.end_date} • {trip.traveler_count} Traveler(s)
          </p>
        </div>
        <div className="flex gap-3">
          <Button 
            className="bg-indigo-600 hover:bg-indigo-700 text-white shadow-md flex items-center gap-2"
            onClick={() => setIsAgentDrawerOpen(true)}
          >
            <Bot className="w-5 h-5" /> TravelPilot Assistant
          </Button>
        </div>
      </div>

      <TripHealthCards trip={trip} />

      {proposal && proposalType && (
        <ProposalReviewModal 
          proposal={proposal} 
          type={proposalType} 
          onApply={handleApplyProposal} 
          onReject={handleRejectProposal} 
        />
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mt-8">
        
        {/* Left Column: Itinerary */}
        <div className="lg:col-span-2 space-y-8">
          
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2 text-gray-800">Route</h3>
            <div className="flex items-center space-x-4 overflow-x-auto pb-4">
               {trip.stops.map((stop: any, i: number) => (
                 <React.Fragment key={stop.id}>
                    <div className="font-semibold bg-blue-50 text-blue-700 border border-blue-200 px-5 py-2.5 rounded-full whitespace-nowrap shadow-sm">
                      {stop.destination_name}
                    </div>
                    {i < trip.stops.length - 1 && <div className="text-gray-400">→</div>}
                 </React.Fragment>
               ))}
            </div>
          </div>

          <div className="space-y-6">
            <h3 className="text-2xl font-bold text-gray-900 mb-2">Itinerary Timeline</h3>
            {trip.stops.map((stop: any) => {
              const stopItems = (trip.itinerary || []).filter((i: any) => i.trip_stop_id === stop.id);
              return <DayItinerary key={stop.id} stop={stop} items={stopItems} />;
            })}
          </div>
        </div>
        
        {/* Right Column: Agent & Tools */}
        <div className="space-y-6">
          
          <DisruptionPanel tripId={trip.id} onProposal={(p) => handleProposalReceived(p, 'replan')} />
          
          <SimulationPanel tripId={trip.id} onSimulation={(s) => handleProposalReceived(s, 'simulation')} />

          <Card className="shadow-sm border-gray-200">
             <CardHeader className="bg-gray-50 border-b pb-4">
               <CardTitle className="text-gray-800 flex items-center gap-2">
                 <Activity className="w-5 h-5 text-indigo-500" />
                 Agent Activity Log
               </CardTitle>
             </CardHeader>
             <CardContent className="pt-4 max-h-[600px] overflow-y-auto">
               {tripId && <AgentEventTimeline tripId={tripId} refreshKey={refreshKey} />}
             </CardContent>
          </Card>
        </div>
      </div>

      {tripId && (
        <AgentChatDrawer 
          tripId={tripId} 
          isOpen={isAgentDrawerOpen} 
          onClose={() => setIsAgentDrawerOpen(false)} 
        />
      )}
    </div>
  );
}
