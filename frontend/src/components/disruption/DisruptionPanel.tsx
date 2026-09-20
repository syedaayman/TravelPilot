import React, { useState } from 'react';
import { triggerDisruption } from '../../api/disruptions';
import { Button } from '../common/Button';
import { Input } from '../common/Input';
import { AlertTriangle, Clock, CloudRain, CreditCard, Ban, Calendar } from 'lucide-react';
import type { CoreDisruptionType } from '../../types';

interface DisruptionPanelProps {
  tripId: string;
  onProposal: (proposal: any) => void;
}

const DISRUPTION_TYPES: { type: CoreDisruptionType; label: string; icon: React.ReactNode; desc: string }[] = [
  { type: 'VENUE_CLOSED', label: 'Venue Closed', icon: <Ban className="w-5 h-5 text-red-500"/>, desc: 'A planned location is suddenly unavailable.' },
  { type: 'WEATHER_ALERT', label: 'Weather Alert', icon: <CloudRain className="w-5 h-5 text-blue-500"/>, desc: 'Rain or severe weather forces indoor activities.' },
  { type: 'BUDGET_REDUCTION', label: 'Budget Cut', icon: <CreditCard className="w-5 h-5 text-green-600"/>, desc: 'Need to lower costs unexpectedly.' },
  { type: 'TRANSPORT_DELAY', label: 'Transport Delayed', icon: <Clock className="w-5 h-5 text-orange-500"/>, desc: 'A flight or train is running late.' },
  { type: 'TRANSPORT_CANCELLED', label: 'Transport Cancelled', icon: <AlertTriangle className="w-5 h-5 text-red-600"/>, desc: 'Find alternative travel arrangements.' },
  { type: 'BOOKING_UNAVAILABLE', label: 'Booking Failed', icon: <Ban className="w-5 h-5 text-gray-500"/>, desc: 'Hotel or critical booking fell through.' },
  { type: 'SCHEDULE_CONFLICT', label: 'Schedule Conflict', icon: <Calendar className="w-5 h-5 text-purple-500"/>, desc: 'Overlapping events need resolution.' },
];

export function DisruptionPanel({ tripId, onProposal }: DisruptionPanelProps) {
  const [selectedType, setSelectedType] = useState<CoreDisruptionType>('VENUE_CLOSED');
  const [reductionAmount, setReductionAmount] = useState<string>('5000');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleTrigger = async () => {
    setLoading(true);
    setError('');
    
    try {
      const payload: any = {
        trip_id: tripId,
        type: selectedType,
      };

      if (selectedType === 'BUDGET_REDUCTION') {
        payload.reduction_amount = parseFloat(reductionAmount);
      }
      
      const res = await triggerDisruption(payload);
      onProposal(res.proposed_replan);
    } catch (err: any) {
      setError(err.message || 'Failed to trigger disruption');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
      <div className="flex items-center gap-2 mb-4">
        <AlertTriangle className="w-5 h-5 text-red-500" />
        <h3 className="text-xl font-semibold text-gray-900">Disruption Center</h3>
      </div>
      <p className="text-sm text-gray-500 mb-6">Test the system's ability to recover from unexpected travel issues.</p>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
        {DISRUPTION_TYPES.map((d) => (
          <button
            key={d.type}
            onClick={() => setSelectedType(d.type)}
            className={`flex flex-col text-left p-3 rounded-xl border transition-all ${
              selectedType === d.type 
                ? 'border-red-500 bg-red-50 shadow-sm ring-1 ring-red-500' 
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

      {selectedType === 'BUDGET_REDUCTION' && (
        <div className="mb-6 bg-gray-50 p-4 rounded-lg border border-gray-100">
          <label className="block text-sm font-medium text-gray-700 mb-2">Reduction Amount (₹)</label>
          <Input 
            type="number" 
            value={reductionAmount} 
            onChange={(e) => setReductionAmount(e.target.value)} 
            placeholder="e.g. 5000"
            className="max-w-[200px]"
          />
        </div>
      )}

      {error && <div className="text-red-500 text-sm mb-4 p-3 bg-red-50 rounded-lg">{error}</div>}
      
      <div title={!tripId ? "Please load a valid trip first." : ""}>
        <Button 
          onClick={handleTrigger} 
          disabled={loading || !tripId} 
          className="w-full bg-red-600 hover:bg-red-700 text-white font-medium py-2.5 shadow-sm"
        >
          {loading ? 'Finding Feasible Alternatives...' : 'Trigger Disruption & Replan'}
        </Button>
      </div>
    </div>
  );
}
