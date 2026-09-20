import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '../components/common/Card';
import { Input } from '../components/common/Input';
import { Button } from '../components/common/Button';
import { planTrip } from '../api/trips';
import { getDestinations } from '../api/destinations';
import type { TripPlanRequest, Destination } from '../types';
import { MapPin, Calendar, Users, Check, Plus, X, List, PlaneTakeoff, Navigation } from 'lucide-react';

const PREDEFINED_INTERESTS = [
  'History', 'Food', 'Culture', 'Beaches', 'Nature', 'Adventure', 'Shopping', 'Nightlife', 'Heritage'
];

export default function PlannerPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const [destinations, setDestinations] = useState<Destination[]>([]);
  
  const [isMultiCity, setIsMultiCity] = useState(false);
  const [selectedDestinations, setSelectedDestinations] = useState<string[]>(['']);
  
  const [startDate, setStartDate] = useState(new Date(Date.now() + 14 * 86400000).toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState(new Date(Date.now() + 20 * 86400000).toISOString().split('T')[0]);
  
  const [budget, setBudget] = useState(40000);
  const [travelers, setTravelers] = useState(2);
  
  const [selectedInterests, setSelectedInterests] = useState<string[]>(['History', 'Food']);
  const [customInterest, setCustomInterest] = useState('');
  
  const [pace, setPace] = useState<'relaxed' | 'moderate' | 'fast'>('moderate');
  const [budgetTier, setBudgetTier] = useState<'budget' | 'mid-range' | 'luxury'>('mid-range');
  const [constraints, setConstraints] = useState('');

  useEffect(() => {
    getDestinations().then(setDestinations).catch(console.error);
  }, []);

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

  const start = new Date(startDate);
  const end = new Date(endDate);
  const duration_days = Math.max(1, Math.ceil((end.getTime() - start.getTime()) / (1000 * 3600 * 24)));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const dests = selectedDestinations.filter(d => d.trim() !== '');
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

  return (
    <div className="max-w-4xl mx-auto py-12 px-4 sm:px-6">
      <div className="text-center mb-10">
        <h1 className="text-4xl font-extrabold text-gray-900 tracking-tight mb-4 flex items-center justify-center gap-3">
          <PlaneTakeoff className="w-10 h-10 text-indigo-600" />
          Intelligent Trip Planning
        </h1>
        <p className="text-xl text-gray-500 max-w-2xl mx-auto">
          Design your perfect itinerary. Our agent will analyze routes, optimize schedules, and manage your budget in real-time.
        </p>
      </div>

      <Card className="shadow-lg border-0 ring-1 ring-gray-200">
        <CardContent className="p-8">
          <form onSubmit={handleSubmit} className="space-y-10">
            
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm flex items-center gap-2">
                <X className="w-4 h-4" /> {error}
              </div>
            )}

            {/* 1. Destination Section */}
            <section className="space-y-4">
              <div className="flex items-center justify-between border-b pb-2">
                <h3 className="text-lg font-bold text-gray-800 flex items-center gap-2">
                  <Navigation className="w-5 h-5 text-indigo-500" />
                  Route & Destinations
                </h3>
                <div className="flex items-center gap-2 bg-gray-50 p-1 rounded-lg border">
                  <button type="button" onClick={() => {setIsMultiCity(false); setSelectedDestinations([selectedDestinations[0] || ''])}} className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${!isMultiCity ? 'bg-white shadow-sm text-indigo-600' : 'text-gray-500 hover:text-gray-700'}`}>Single City</button>
                  <button type="button" onClick={() => setIsMultiCity(true)} className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${isMultiCity ? 'bg-white shadow-sm text-indigo-600' : 'text-gray-500 hover:text-gray-700'}`}>Multi-City</button>
                </div>
              </div>

              <div className="space-y-3 relative">
                {selectedDestinations.map((dest, idx) => (
                  <div key={idx} className="flex items-center gap-3">
                    <div className="flex-1 relative">
                      <MapPin className="w-5 h-5 absolute left-3 top-2.5 text-gray-400" />
                      <select 
                        required
                        className="w-full h-10 pl-10 pr-3 rounded-md border border-gray-300 bg-white text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all appearance-none"
                        value={dest}
                        onChange={(e) => updateDestination(idx, e.target.value)}
                      >
                        <option value="" disabled>Select a destination...</option>
                        {destinations.map(d => (
                          <option key={d.id} value={d.name}>{d.name} {d.state_province ? `(${d.state_province})` : ''}</option>
                        ))}
                      </select>
                    </div>
                    {isMultiCity && idx > 0 && (
                      <button type="button" onClick={() => removeDestination(idx)} className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-md transition-colors">
                        <X className="w-5 h-5" />
                      </button>
                    )}
                  </div>
                ))}
                
                {isMultiCity && (
                  <button type="button" onClick={addDestination} className="text-sm font-medium text-indigo-600 hover:text-indigo-700 flex items-center gap-1 mt-2">
                    <Plus className="w-4 h-4" /> Add another destination
                  </button>
                )}
              </div>
            </section>

            {/* 2. Dates & Travelers */}
            <section className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="space-y-4">
                <h3 className="text-lg font-bold text-gray-800 flex items-center gap-2 border-b pb-2">
                  <Calendar className="w-5 h-5 text-indigo-500" /> Dates
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Start Date</label>
                    <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} required className="w-full" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">End Date</label>
                    <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} required className="w-full" />
                  </div>
                </div>
                <p className="text-sm text-gray-500 font-medium">Trip Duration: <span className="text-indigo-600">{duration_days} days</span></p>
              </div>

              <div className="space-y-4">
                <h3 className="text-lg font-bold text-gray-800 flex items-center gap-2 border-b pb-2">
                  <Users className="w-5 h-5 text-indigo-500" /> Group & Budget
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Travelers</label>
                    <Input type="number" value={travelers} onChange={(e) => setTravelers(Number(e.target.value))} required min="1" className="w-full" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Total Budget (₹)</label>
                    <Input type="number" value={budget} onChange={(e) => setBudget(Number(e.target.value))} required min="1000" step="500" className="w-full font-mono" />
                  </div>
                </div>
              </div>
            </section>

            {/* 3. Interests & Vibe */}
            <section className="space-y-4">
              <h3 className="text-lg font-bold text-gray-800 flex items-center gap-2 border-b pb-2">
                <List className="w-5 h-5 text-indigo-500" /> Vibe & Interests
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="md:col-span-2 space-y-3">
                  <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider">What do you want to do?</label>
                  <div className="flex flex-wrap gap-2">
                    {PREDEFINED_INTERESTS.map(interest => (
                      <button
                        key={interest}
                        type="button"
                        onClick={() => toggleInterest(interest)}
                        className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all border ${selectedInterests.includes(interest) ? 'bg-indigo-50 border-indigo-200 text-indigo-700 shadow-sm' : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300 hover:bg-gray-50'}`}
                      >
                        {selectedInterests.includes(interest) && <Check className="w-3 h-3 inline-block mr-1" />}
                        {interest}
                      </button>
                    ))}
                    {selectedInterests.filter(i => !PREDEFINED_INTERESTS.includes(i)).map(interest => (
                      <button
                        key={interest}
                        type="button"
                        onClick={() => toggleInterest(interest)}
                        className="px-3 py-1.5 rounded-full text-sm font-medium bg-indigo-50 border border-indigo-200 text-indigo-700 shadow-sm transition-all"
                      >
                        <Check className="w-3 h-3 inline-block mr-1" /> {interest}
                      </button>
                    ))}
                  </div>
                  <Input 
                    placeholder="+ Add custom interest (press Enter)" 
                    value={customInterest} 
                    onChange={e => setCustomInterest(e.target.value)}
                    onKeyDown={handleAddCustomInterest}
                    className="w-full max-w-sm mt-2 text-sm"
                  />
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Pace</label>
                    <select value={pace} onChange={(e) => setPace(e.target.value as any)} className="w-full h-10 rounded-md border border-gray-300 bg-white text-sm px-3 focus:ring-2 focus:ring-indigo-500 outline-none">
                      <option value="relaxed">Relaxed</option>
                      <option value="moderate">Moderate</option>
                      <option value="fast">Fast</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Hotel Tier</label>
                    <select value={budgetTier} onChange={(e) => setBudgetTier(e.target.value as any)} className="w-full h-10 rounded-md border border-gray-300 bg-white text-sm px-3 focus:ring-2 focus:ring-indigo-500 outline-none">
                      <option value="budget">Budget</option>
                      <option value="mid-range">Mid-Range</option>
                      <option value="luxury">Luxury</option>
                    </select>
                  </div>
                </div>
              </div>
            </section>

            {/* 4. Constraints */}
            <section className="space-y-3">
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider">Additional Constraints (Optional)</label>
              <textarea 
                value={constraints}
                onChange={e => setConstraints(e.target.value)}
                placeholder="e.g. Vegetarian food only, avoid early morning travel, accessibility requirements..."
                className="w-full min-h-[80px] p-3 rounded-md border border-gray-300 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all resize-y"
              />
            </section>

            <div className="pt-4 border-t">
              <Button type="submit" className="w-full h-12 text-lg font-bold shadow-md bg-indigo-600 hover:bg-indigo-700 text-white transition-all" disabled={loading}>
                {loading ? 'Initializing Agent...' : 'Generate Trip Plan'}
              </Button>
              
              {loading && (
                <div className="mt-6 p-4 rounded-xl bg-indigo-50 border border-indigo-100 flex flex-col items-center justify-center space-y-3">
                  <div className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
                  <p className="text-sm font-medium text-indigo-800 text-center animate-pulse">
                    The TravelPilot agent is currently analyzing your request. <br/>
                    Please wait while we resolve destinations, compute travel times, and generate your optimized itinerary...
                  </p>
                </div>
              )}
            </div>
            
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
