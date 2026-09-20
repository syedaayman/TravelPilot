import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { planTrip } from '../api/trips';
import { getDestinations } from '../api/destinations';
import type { TripPlanRequest, Destination } from '../types';
import { MapPin, Calendar, Users, Check, Plus, X, Navigation, ArrowRight, Sparkles, ShieldCheck, Compass } from 'lucide-react';

const PREDEFINED_INTERESTS = [
  'Heritage', 'Food', 'Culture', 'Textiles', 'Crafts', 'Nature', 'Beaches', 'Art', 'Shopping', 'Nightlife', 'Photography'
];

const PROGRESS_STEPS = [
  "Understanding your trip & preferences...",
  "Resolving destination catalogue reference layers...",
  "Selecting iconic heritage, crafts & textile experiences...",
  "Curating authentic local food & dining recommendations...",
  "Optimizing inter-city transit & travel times...",
  "Allocating accommodation tiers & budget bounds...",
  "Validating schedule invariants & zero conflicts...",
  "Finalizing your TravelPilot travel diary..."
];

export default function PlannerPage() {
  const navigate = useNavigate();
  const [showSplash, setShowSplash] = useState(false);

  const [loading, setLoading] = useState(false);
  const [progressStepIdx, setProgressStepIdx] = useState(0);
  const [error, setError] = useState('');
  
  const [destinations, setDestinations] = useState<Destination[]>([]);
  
  const [isMultiCity, setIsMultiCity] = useState(true);
  const [selectedDestinations, setSelectedDestinations] = useState<string[]>(['Hyderabad', 'Goa']);
  
  const [startDate, setStartDate] = useState(new Date(Date.now() + 14 * 86400000).toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState(new Date(Date.now() + 21 * 86400000).toISOString().split('T')[0]);
  
  const [budget, setBudget] = useState(40000);
  const [travelers, setTravelers] = useState(3);
  
  const [selectedInterests, setSelectedInterests] = useState<string[]>(['Heritage', 'Food', 'Culture']);

  const [customInterest, setCustomInterest] = useState('');
  
  const [pace] = useState<'relaxed' | 'moderate' | 'fast'>('moderate');
  const [budgetTier] = useState<'budget' | 'mid-range' | 'luxury'>('mid-range');
  const [constraints] = useState('');

  useEffect(() => {
    getDestinations().then(setDestinations).catch(console.error);
  }, []);

  useEffect(() => {
    if (loading) {
      const interval = setInterval(() => {
        setProgressStepIdx(prev => (prev < PROGRESS_STEPS.length - 1 ? prev + 1 : prev));
      }, 700);
      return () => clearInterval(interval);
    }
  }, [loading]);

  const loadDemoScenario = () => {
    setIsMultiCity(true);
    setSelectedDestinations(['Hyderabad', 'Hampi', 'Goa']);
    const start = new Date();
    start.setDate(start.getDate() + 14);
    const end = new Date(start);
    end.setDate(end.getDate() + 7); // 8 days total
    setStartDate(start.toISOString().split('T')[0]);
    setEndDate(end.toISOString().split('T')[0]);
    setBudget(40000);
    setTravelers(3);
    setSelectedInterests(['Heritage', 'Food', 'Culture', 'Beaches']);
    setShowSplash(false);
  };

  const addDestination = () => setSelectedDestinations([...selectedDestinations, '']);
  const removeDestination = (idx: number) => setSelectedDestinations(selectedDestinations.filter((_, i) => i !== idx));
  const updateDestination = (idx: number, val: string) => {
    const next = [...selectedDestinations];
    next[idx] = val;
    setSelectedDestinations(next);
  };

  const toggleInterest = (interest: string) => {
    if (selectedInterests.includes(interest)) {
      setSelectedInterests(selectedInterests.filter(i => i !== interest));
    } else {
      setSelectedInterests([...selectedInterests, interest]);
    }
  };

  const handleAddCustomInterest = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && customInterest.trim()) {
      e.preventDefault();
      if (!selectedInterests.includes(customInterest.trim())) {
        setSelectedInterests([...selectedInterests, customInterest.trim()]);
      }
      setCustomInterest('');
    }
  };

  const start = new Date(`${startDate}T00:00:00`);
  const end = new Date(`${endDate}T00:00:00`);
  const duration_days = Math.max(1, Math.floor((end.getTime() - start.getTime()) / 86400000) + 1);
  const accommodationNights = Math.max(0, duration_days - 1);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setProgressStepIdx(0);
    setError('');

    const dests = Array.from(new Set(selectedDestinations.filter(d => d.trim() !== '')));

    if (dests.length === 0) {
      setError('Please select at least one destination.');
      setLoading(false);
      return;
    }

    const req: TripPlanRequest = {
      destinations: dests,
      duration_days,
      budget: Number(budget),
      travelers: Number(travelers),
      start_date: startDate,
      end_date: endDate,
      interests: selectedInterests,
      constraints: constraints || undefined,
      preferences: {
        pace,
        budget_tier: budgetTier,
      }
    };

    try {
      const trip = await planTrip(req);
      navigate(`/trip/${trip.id}`);
    } catch (err: any) {
      setError(err.message || 'Failed to plan trip');
      setLoading(false);
    }
  };

  // Screen 1: Splash / Intro
  if (showSplash) {
    return (
      <div className="min-h-[calc(100vh-4rem)] flex flex-col items-center justify-center relative overflow-hidden py-12 px-4 sm:px-6 bg-slate-50">
        <div className="max-w-2xl w-full text-center space-y-8 relative z-10">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-blue-50 border border-blue-200 text-xs font-mono font-bold text-blue-700 shadow-sm">
            <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse" />
            TRAVELPILOT AGENT SYSTEM 2.0 ONLINE
          </div>

          <div className="space-y-3">
            <h1 className="text-4xl sm:text-5xl font-black text-slate-900 tracking-tight leading-none">
              TRAVEL <span className="text-blue-600">PILOT</span>
            </h1>
            <p className="text-xl font-medium text-slate-600 tracking-wide">
              Intelligent trip planning. Designed for the journey, ready for the unexpected.
            </p>
          </div>

          <p className="text-xs sm:text-sm text-slate-600 max-w-lg mx-auto leading-relaxed">
            Experience complete travel diary planning with heritage, food, textiles, local crafts, and autonomous disruption management.
          </p>

          <div className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-4">
            <button
              onClick={() => setShowSplash(false)}
              className="w-full sm:w-auto px-8 py-3.5 rounded-xl font-bold bg-blue-600 hover:bg-blue-700 text-white shadow-md transition-all flex items-center justify-center gap-2 text-sm"
            >
              Continue to Planner <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={loadDemoScenario}
              className="w-full sm:w-auto px-6 py-3.5 rounded-xl font-semibold bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 shadow-sm transition-all flex items-center justify-center gap-2 text-xs"
            >
              <Sparkles className="w-4 h-4 text-blue-600" /> Preset: Hyderabad → Hampi → Goa
            </button>
          </div>

          <div className="pt-6 grid grid-cols-3 gap-4 border-t border-slate-200 text-left">
            <div className="p-3.5 rounded-xl bg-white border border-slate-200 shadow-sm">
              <Compass className="w-4 h-4 text-blue-600 mb-1" />
              <div className="text-xs font-bold text-slate-900">Travel Diary</div>
              <div className="text-[11px] text-slate-500">Food, culture & crafts</div>
            </div>
            <div className="p-3.5 rounded-xl bg-white border border-slate-200 shadow-sm">
              <ShieldCheck className="w-4 h-4 text-blue-600 mb-1" />
              <div className="text-xs font-bold text-slate-900">Deterministic Engine</div>
              <div className="text-[11px] text-slate-500">Zero duplicate days/items</div>
            </div>
            <div className="p-3.5 rounded-xl bg-white border border-slate-200 shadow-sm">
              <Sparkles className="w-4 h-4 text-blue-600 mb-1" />
              <div className="text-xs font-bold text-slate-900">What-If & Replanning</div>
              <div className="text-[11px] text-slate-500">Autonomous recovery</div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Screen 2: Planner Form
  return (
    <div className="max-w-4xl mx-auto py-10 px-4 sm:px-6 relative">
      <div className="flex items-center justify-between mb-8 pb-4 border-b border-slate-200">
        <div>
          <p className="text-[11px] font-mono text-blue-600 uppercase tracking-widest mb-1">
            Intelligent Trip Planning & Disruption Engine
          </p>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight flex items-center gap-2.5">
            <Navigation className="w-6 h-6 text-blue-600" />
            Plan Your Journey
          </h1>
        </div>

        <button
          onClick={loadDemoScenario}
          className="px-4 py-2 rounded-lg bg-blue-50 hover:bg-blue-100 border border-blue-200 text-blue-700 text-xs font-bold flex items-center gap-1.5 transition-all shadow-sm"
        >
          <Sparkles className="w-3.5 h-3.5 text-blue-600" /> Preset: Hyderabad → Hampi → Goa
        </button>
      </div>

      <div className="bg-white rounded-2xl p-6 sm:p-8 shadow-sm border border-slate-200 relative">
        <form onSubmit={handleSubmit} className="space-y-8">
          
          {error && (
            <div className="bg-rose-50 border border-rose-200 text-rose-700 px-4 py-3 rounded-xl text-xs font-medium flex items-center gap-2">
              <X className="w-4 h-4 shrink-0" /> {error}
            </div>
          )}

          {/* 1. Route & Destinations */}
          <section className="space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <MapPin className="w-4 h-4 text-blue-600" />
                Route & Destinations
              </h3>
              <div className="flex items-center gap-2 bg-slate-100 p-1 rounded-lg border border-slate-200 text-xs">
                <button 
                  type="button" 
                  onClick={() => {setIsMultiCity(false); setSelectedDestinations([selectedDestinations[0] || 'Hyderabad']);}} 
                  className={`px-3 py-1 font-medium rounded-md transition-colors ${!isMultiCity ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}
                >
                  Single City
                </button>
                <button 
                  type="button" 
                  onClick={() => {setIsMultiCity(true); if(selectedDestinations.length < 2) setSelectedDestinations(['Hyderabad', 'Hampi', 'Goa']);}} 
                  className={`px-3 py-1 font-medium rounded-md transition-colors ${isMultiCity ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}
                >
                  Multi-City
                </button>
              </div>
            </div>

            {isMultiCity && selectedDestinations.filter(d => d).length > 0 && (
              <div className="p-3.5 rounded-xl bg-blue-50/50 border border-blue-200 flex items-center gap-2 overflow-x-auto custom-scrollbar">
                <span className="text-xs font-mono text-slate-500 uppercase tracking-widest mr-2 whitespace-nowrap">Route Stepper:</span>
                {selectedDestinations.filter(d => d).map((d, idx) => (
                  <React.Fragment key={idx}>
                    <span className="px-3 py-1 rounded-md bg-white border border-blue-200 text-blue-700 font-bold text-xs whitespace-nowrap shadow-sm">
                      {d}
                    </span>
                    {idx < selectedDestinations.filter(d => d).length - 1 && (
                      <span className="text-slate-400 font-bold text-xs">→</span>
                    )}
                  </React.Fragment>
                ))}
              </div>
            )}

            <div className="space-y-3">
              {selectedDestinations.map((dest, idx) => (
                <div key={idx} className="flex items-center gap-3">
                  <div className="flex-1 relative">
                    <MapPin className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
                    <select 
                      className="w-full h-10 pl-9 pr-3 rounded-xl border border-slate-200 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all appearance-none"
                      value={dest}
                      onChange={(e) => updateDestination(idx, e.target.value)}
                    >

                      <option value="" disabled>Select destination...</option>
                      {destinations.map(d => (
                        <option key={d.id} value={d.name}>{d.name} {d.state_province ? `(${d.state_province})` : ''}</option>
                      ))}
                    </select>
                  </div>
                  {isMultiCity && idx > 0 && (
                    <button 
                      type="button" 
                      onClick={() => removeDestination(idx)} 
                      className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
              
              {isMultiCity && (
                <button 
                  type="button" 
                  onClick={addDestination} 
                  className="text-xs font-bold text-blue-600 hover:text-blue-700 flex items-center gap-1 pt-1"
                >
                  <Plus className="w-3.5 h-3.5" /> + Add another destination
                </button>
              )}
            </div>
          </section>

          {/* 2. Dates & Group */}
          <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2 border-b border-slate-200 pb-3">
                <Calendar className="w-4 h-4 text-blue-600" /> Dates
              </h3>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-mono text-slate-500 uppercase tracking-wider mb-1">Start Date</label>
                  <input 
                    type="date" 
                    value={startDate} 
                    onChange={e => setStartDate(e.target.value)}
                    className="w-full h-10 px-3 rounded-xl border border-slate-200 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" 
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-mono text-slate-500 uppercase tracking-wider mb-1">End Date</label>
                  <input 
                    type="date" 
                    value={endDate} 
                    onChange={e => setEndDate(e.target.value)}
                    className="w-full h-10 px-3 rounded-xl border border-slate-200 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" 
                  />
                </div>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex justify-between text-xs text-slate-600 font-mono">
                <span>Duration: <strong className="text-slate-900">{duration_days} Days</strong></span>
                <span>Stays: <strong className="text-slate-900">{accommodationNights} Nights</strong></span>
              </div>
            </div>

            <div className="space-y-4">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2 border-b border-slate-200 pb-3">
                <Users className="w-4 h-4 text-blue-600" /> Travelers & Budget Cap
              </h3>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-mono text-slate-500 uppercase tracking-wider mb-1">Travelers</label>
                  <input 
                    type="number" 
                    min="1" 
                    max="20" 
                    value={travelers} 
                    onChange={e => setTravelers(Number(e.target.value))}
                    className="w-full h-10 px-3 rounded-xl border border-slate-200 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" 
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-mono text-slate-500 uppercase tracking-wider mb-1">Max Budget (₹)</label>
                  <input 
                    type="number" 
                    step="1000" 
                    value={budget} 
                    onChange={e => setBudget(Number(e.target.value))}
                    className="w-full h-10 px-3 rounded-xl border border-slate-200 bg-white text-slate-900 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" 
                  />
                </div>
              </div>
            </div>
          </section>

          {/* 3. Interests */}
          <section className="space-y-4">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2 border-b border-slate-200 pb-3">
              <Sparkles className="w-4 h-4 text-blue-600" />
              Interests & Local Experience Focus
            </h3>

            <div className="flex flex-wrap gap-2">
              {PREDEFINED_INTERESTS.map(interest => {
                const isSelected = selectedInterests.includes(interest);
                return (
                  <button
                    key={interest}
                    type="button"
                    onClick={() => toggleInterest(interest)}
                    className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 border ${
                      isSelected 
                        ? 'bg-blue-600 text-white border-blue-600 shadow-sm' 
                        : 'bg-white text-slate-700 border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                    }`}
                  >
                    {isSelected && <Check className="w-3.5 h-3.5" />}
                    {interest}
                  </button>
                );
              })}
            </div>

            <div className="pt-2">
              <input 
                type="text" 
                placeholder="Type custom interest (e.g. Biryani, Ikat, Architecture) and press Enter" 
                value={customInterest} 
                onChange={e => setCustomInterest(e.target.value)}
                onKeyDown={handleAddCustomInterest}
                className="w-full h-10 px-3.5 rounded-xl border border-slate-200 bg-white text-slate-900 text-xs placeholder-slate-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" 
              />
            </div>
          </section>

          {/* Submit Action */}
          <div className="pt-4">
            <button
              type="submit"
              disabled={loading}
              className="w-full py-4 rounded-xl font-bold bg-blue-600 hover:bg-blue-700 text-white shadow-md transition-all flex items-center justify-center gap-2 text-base disabled:opacity-50"
            >
              {loading ? (
                <>Generating Deterministic Travel Plan...</>
              ) : (
                <>
                  <Navigation className="w-5 h-5" /> Generate Trip Plan
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Progress Overlay Modal */}
      {loading && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-2xl max-w-md w-full p-6 space-y-6 shadow-xl text-center">
            <div className="w-12 h-12 rounded-full bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 mx-auto animate-spin">
              <Navigation className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900">Planning Your Journey</h3>
              <p className="text-xs text-blue-600 font-mono mt-1 font-semibold">{PROGRESS_STEPS[progressStepIdx]}</p>
            </div>
            <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
              <div 
                className="bg-blue-600 h-full transition-all duration-500"
                style={{ width: `${((progressStepIdx + 1) / PROGRESS_STEPS.length) * 100}%` }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
