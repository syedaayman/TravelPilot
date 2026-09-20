import React, { useState } from 'react';
import { triggerSimulation } from '../../api/simulations';
import { Button } from '../common/Button';
import { Input } from '../common/Input';
import { Sparkles, DollarSign, CalendarPlus, MapPinOff, Replace, PlusCircle } from 'lucide-react';
import type { WhatIfType } from '../../types';

interface SimulationPanelProps {
  tripId: string;
  onSimulation: (result: any) => void;
}

const SIMULATION_TYPES: { type: WhatIfType; label: string; icon: React.ReactNode; desc: string }[] = [
  { type: 'BUDGET_CHANGE', label: 'Change Budget', icon: <DollarSign className="w-5 h-5 text-emerald-500"/>, desc: 'Increase or decrease total budget.' },
  { type: 'ADD_DAY', label: 'Add Extra Day', icon: <CalendarPlus className="w-5 h-5 text-blue-500"/>, desc: 'Extend the trip duration.' },
  { type: 'REMOVE_DESTINATION', label: 'Skip Destination', icon: <MapPinOff className="w-5 h-5 text-red-500"/>, desc: 'Remove a stop from multi-city trips.' },
  { type: 'REPLACE_DESTINATION', label: 'Swap Destination', icon: <Replace className="w-5 h-5 text-purple-500"/>, desc: 'Change one city for another.' },
  { type: 'ADD_ACTIVITY', label: 'Add Custom Activity', icon: <PlusCircle className="w-5 h-5 text-orange-500"/>, desc: 'Inject a new event into the itinerary.' },
];

export function SimulationPanel({ tripId, onSimulation }: SimulationPanelProps) {
  const [selectedType, setSelectedType] = useState<WhatIfType>('BUDGET_CHANGE');
  const [amount, setAmount] = useState<string>('5000');
  const [days, setDays] = useState<string>('1');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleTrigger = async () => {
    setLoading(true);
    setError('');
    
    try {
      const payload: any = {
        trip_id: tripId,
        type: selectedType,
        parameters: {}
      };

      if (selectedType === 'BUDGET_CHANGE') {
        payload.parameters.new_budget = parseFloat(amount); // Requires exact API schema match, we might use delta
      } else if (selectedType === 'ADD_DAY') {
        payload.parameters.extra_days = parseInt(days, 10);
      }
      
      const res = await triggerSimulation(payload);
      onSimulation(res);
    } catch (err: any) {
      setError(err.message || 'Failed to simulate what-if scenario');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
      <div className="flex items-center gap-2 mb-4">
        <Sparkles className="w-5 h-5 text-blue-600" />
        <h3 className="text-xl font-semibold text-gray-900">What-If Studio</h3>
      </div>
      <p className="text-sm text-gray-500 mb-6">Safely experiment with changes without altering your active plan.</p>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
        {SIMULATION_TYPES.map((d) => (
          <button
            key={d.type}
            onClick={() => setSelectedType(d.type)}
            className={`flex flex-col text-left p-3 rounded-xl border transition-all ${
              selectedType === d.type 
                ? 'border-blue-500 bg-blue-50 shadow-sm ring-1 ring-blue-500' 
                : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
            }`}
          >
            <div className="flex items-center gap-2 font-medium text-gray-900 mb-1">
              {d.icon}
              {d.label}
            </div>
            <span className="text-xs text-gray-500 leading-tight">{d.desc}</span>
          </button>
        ))}
      </div>

      {selectedType === 'BUDGET_CHANGE' && (
        <div className="mb-6 bg-gray-50 p-4 rounded-lg border border-gray-100">
          <label className="block text-sm font-medium text-gray-700 mb-2">New Target Budget (₹)</label>
          <Input 
            type="number" 
            value={amount} 
            onChange={(e) => setAmount(e.target.value)} 
            placeholder="e.g. 30000"
            className="max-w-[200px]"
          />
        </div>
      )}

      {selectedType === 'ADD_DAY' && (
        <div className="mb-6 bg-gray-50 p-4 rounded-lg border border-gray-100">
          <label className="block text-sm font-medium text-gray-700 mb-2">Extra Days</label>
          <Input 
            type="number" 
            value={days} 
            onChange={(e) => setDays(e.target.value)} 
            placeholder="e.g. 1"
            className="max-w-[200px]"
            min="1"
            max="5"
          />
        </div>
      )}

      {error && <div className="text-red-500 text-sm mb-4 p-3 bg-red-50 rounded-lg">{error}</div>}
      
      <div title={!tripId ? "Please load a valid trip first." : ""}>
        <Button 
          onClick={handleTrigger} 
          disabled={loading || !tripId} 
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 shadow-sm"
        >
          {loading ? 'Simulating Changes...' : 'Run Simulation'}
        </Button>
      </div>
    </div>
  );
}
