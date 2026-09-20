import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getTrip } from '../api/trips';
import type { TripDetailResponse } from '../types';
import { TripHealthCards } from '../components/dashboard/TripHealthCards';
import { HotelExperienceCard } from '../components/dashboard/HotelExperienceCard';
import { FoodDiscoveryCard } from '../components/dashboard/FoodDiscoveryCard';
import { CultureDiscoveryCard } from '../components/dashboard/CultureDiscoveryCard';
import { DiscoverDestinationModal } from '../components/dashboard/DiscoverDestinationModal';
import { AddActivityModal } from '../components/dashboard/AddActivityModal';
import { DayItinerary } from '../components/itinerary/DayItinerary';
import { Button } from '../components/common/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/common/Card';
import { applyReplan, rejectReplan } from '../api/disruptions';
import { applySimulation, rejectSimulation } from '../api/simulations';

import { Bot, Activity, PlusCircle, Compass, MapPin, ArrowLeft, RefreshCw, Sparkles } from 'lucide-react';


import { AgentChatDrawer } from '../components/agent/AgentChatDrawer';
import { AgentEventTimeline } from '../components/agent/AgentEventTimeline';
import { DisruptionPanel } from '../components/disruption/DisruptionPanel';
import { SimulationPanel } from '../components/simulation/SimulationPanel';
import { ProposalReviewModal } from '../components/common/ProposalReviewModal';

export default function TripDashboardPage() {
  const { tripId } = useParams();
  const navigate = useNavigate();
  const [trip, setTrip] = useState<TripDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  const [refreshKey, setRefreshKey] = useState(0);

  const [isAgentDrawerOpen, setIsAgentDrawerOpen] = useState(false);
  const [isAddActivityOpen, setIsAddActivityOpen] = useState(false);
  const [selectedCultureDestId, setSelectedCultureDestId] = useState<string | null>(null);

  const [proposal, setProposal] = useState<any>(null);
  const [proposalType, setProposalType] = useState<'replan' | 'simulation' | null>(null);

  const fetchTrip = () => {
    if (!tripId) return;
    setLoading(true);
    getTrip(tripId)
      .then(t => {
        setTrip(t);
        setRefreshKey(prev => prev + 1);
      })
      .catch((err) => {
        setError(err.message || 'Failed to load trip');
        setTrip(null);
        localStorage.removeItem('active_trip_id');
      })
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

  if (loading && !trip) {
    return (
      <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col items-center justify-center p-6">
        <div className="w-12 h-12 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 mb-4 animate-spin">
          <RefreshCw className="w-6 h-6" />
        </div>
        <p className="text-xs font-semibold text-slate-600 animate-pulse">Loading TravelPilot Itinerary & Real-Time Engines...</p>
      </div>
    );
  }

  if (error || !trip) {
    return (
      <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col items-center justify-center p-6 text-center">
        <div className="max-w-md p-8 bg-white border border-slate-200 rounded-2xl space-y-4 shadow-sm">
          <h2 className="text-lg font-bold text-rose-600">Trip Not Found</h2>
          <p className="text-xs text-slate-500">
            The requested trip could not be retrieved from the server or has expired.
          </p>
          <Button 
            onClick={() => navigate('/')} 
            className="w-full bg-blue-600 hover:bg-blue-700 text-white text-xs py-2.5"
          >
            Plan a New Multi-City Trip
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans selection:bg-blue-600 selection:text-white pb-16">
      
      {/* Secondary Navbar Control Bar */}
      <div className="bg-white border-b border-slate-200 py-3 shadow-sm sticky top-16 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/')}
              className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors"
              title="Return to Planner"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-lg font-extrabold text-slate-900 tracking-tight leading-tight">
                {trip.title}
              </h1>
              <p className="text-[11px] text-slate-500 font-medium">
                {trip.start_date} to {trip.end_date} · {trip.traveler_count} Traveler(s)
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <Button
              onClick={() => setIsAddActivityOpen(true)}
              variant="secondary"
              className="text-xs py-1.5 px-3 border-slate-200 text-slate-700 hover:bg-slate-50 flex items-center gap-1.5"
            >
              <PlusCircle className="w-4 h-4 text-blue-600" />
              <span className="hidden md:inline">Add Feasible Activity</span>
            </Button>

            <Button
              onClick={() => setSelectedCultureDestId(trip.stops[0]?.destination_id || trip.stops[0]?.destination_name)}
              variant="secondary"
              className="text-xs py-1.5 px-3 border-slate-200 text-slate-700 hover:bg-slate-50 flex items-center gap-1.5"
            >
              <Compass className="w-4 h-4 text-blue-600" />
              <span className="hidden md:inline">Discover Culture</span>
            </Button>

            <Button 
              className="text-xs py-2 px-4 bg-blue-600 hover:bg-blue-700 text-white shadow-sm flex items-center gap-2 font-bold"
              onClick={() => setIsAgentDrawerOpen(true)}
            >
              <Bot className="w-4 h-4" /> TravelPilot AI
            </Button>
          </div>
        </div>
      </div>

      {/* Main Dashboard Container */}
      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 space-y-8">
        
        {/* Route Stepper Card */}
        <div className="p-5 bg-white border border-slate-200 rounded-2xl shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
              <MapPin className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-full">
                Multi-City Route Stepper
              </span>
              <h2 className="text-base font-bold text-slate-900 mt-0.5">
                {trip.stops.map(s => s.destination_name).join(' → ')}
              </h2>
            </div>
          </div>

          <div className="flex items-center gap-2 overflow-x-auto py-1">
            {trip.stops.map((stop: any, idx: number) => (
              <React.Fragment key={stop.id}>
                <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 text-xs font-bold whitespace-nowrap">
                  <span>{stop.destination_name}</span>
                  <span className="text-[10px] text-slate-500 font-mono">({stop.duration_days}d)</span>
                </div>
                {idx < trip.stops.length - 1 && (
                  <span className="text-slate-400 text-xs font-bold">→</span>
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Health & Engine Metrics */}
        <TripHealthCards trip={trip} />

        {/* Proposal Review Modal if active */}
        {proposal && proposalType && (
          <ProposalReviewModal 
            proposal={proposal} 
            type={proposalType} 
            onApply={handleApplyProposal} 
            onReject={handleRejectProposal} 
          />
        )}

        {/* Hotel & Stay Swapping Hub */}
        <HotelExperienceCard trip={trip} onTripUpdated={fetchTrip} />

        {/* Cultural & Culinary Discovery Cards */}
        <div className="space-y-6">
          <FoodDiscoveryCard stops={trip.stops} />
          <CultureDiscoveryCard 
            stops={trip.stops} 
            onOpenCultureModal={(destId) => setSelectedCultureDestId(destId)} 
          />
        </div>

        {/* Main Grid: Itinerary Timeline vs Disruption/Simulation Tools */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 pt-2">
          
          {/* Left Column: Itinerary Timeline */}
          <div className="lg:col-span-2 space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-blue-600" /> Complete Travel Diary Timeline
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Sequential daily schedule with morning, afternoon & evening experiences.
                </p>
              </div>

              <Button
                onClick={() => setIsAddActivityOpen(true)}
                variant="secondary"
                className="text-xs py-1 px-3 border-blue-200 text-blue-700 hover:bg-blue-50 flex items-center gap-1"
              >
                <PlusCircle className="w-3.5 h-3.5" /> Add Activity
              </Button>
            </div>

            <div className="space-y-6">
              {trip.stops.map((stop: any) => {
                const stopItems = (trip.itinerary || []).filter((i: any) => i.trip_stop_id === stop.id);
                return <DayItinerary key={stop.id} stop={stop} items={stopItems} />;
              })}
            </div>
          </div>
          
          {/* Right Column: Engine Panels & Log */}
          <div className="space-y-6">
            
            {/* Disruption Management Engine */}
            <DisruptionPanel tripId={trip.id} onProposal={(p) => handleProposalReceived(p, 'replan')} />
            
            {/* What-If Simulator */}
            <SimulationPanel tripId={trip.id} onSimulation={(s) => handleProposalReceived(s, 'simulation')} />

            {/* Agent Activity Audit Log */}
            <Card className="bg-white border-slate-200 shadow-sm">
               <CardHeader className="bg-slate-50 border-b border-slate-200 p-4">
                 <CardTitle className="text-slate-900 text-sm font-bold flex items-center gap-2">
                   <Activity className="w-4 h-4 text-blue-600" />
                   Agent Execution Audit Log
                 </CardTitle>
               </CardHeader>
               <CardContent className="p-4 max-h-[450px] overflow-y-auto">
                 {tripId && <AgentEventTimeline tripId={tripId} refreshKey={refreshKey} />}
               </CardContent>
            </Card>
          </div>
        </div>
      </main>

      {/* Slide-Over Drawers & Modals */}
      {tripId && (
        <AgentChatDrawer 
          tripId={tripId} 
          isOpen={isAgentDrawerOpen} 
          onClose={() => setIsAgentDrawerOpen(false)} 
        />
      )}

      {selectedCultureDestId && (
        <DiscoverDestinationModal
          destinationIdOrName={selectedCultureDestId}
          onClose={() => setSelectedCultureDestId(null)}
        />
      )}

      {isAddActivityOpen && (
        <AddActivityModal
          trip={trip}
          isOpen={isAddActivityOpen}
          onClose={() => setIsAddActivityOpen(false)}
          onActivityAdded={fetchTrip}
        />
      )}
    </div>
  );
}
