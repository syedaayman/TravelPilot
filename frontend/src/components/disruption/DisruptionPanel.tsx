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
  { type: 'VENUE_CLOSED', label: 'Venue Closed', icon: <Ban className="w-4 h-4 text-blue-600"/>, desc: 'A planned location is suddenly unavailable.' },
  { type: 'WEATHER_ALERT', label: 'Weather Alert', icon: <CloudRain className="w-4 h-4 text-blue-600"/>, desc: 'Rain or severe weather forces indoor activities.' },
  { type: 'BUDGET_REDUCTION', label: 'Budget Cut', icon: <CreditCard className="w-4 h-4 text-blue-600"/>, desc: 'Need to lower costs unexpectedly.' },
  { type: 'TRANSPORT_DELAY', label: 'Transport Delayed', icon: <Clock className="w-4 h-4 text-blue-600"/>, desc: 'A flight or train is running late.' },
  { type: 'TRANSPORT_CANCELLED', label: 'Transport Cancelled', icon: <AlertTriangle className="w-4 h-4 text-blue-600"/>, desc: 'Find alternative travel arrangements.' },
  { type: 'BOOKING_UNAVAILABLE', label: 'Booking Failed', icon: <Ban className="w-4 h-4 text-blue-600"/>, desc: 'Hotel or critical booking fell through.' },
  { type: 'SCHEDULE_CONFLICT', label: 'Schedule Conflict', icon: <Calendar className="w-4 h-4 text-blue-600"/>, desc: 'Overlapping events need resolution.' },
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
    <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
      <div className="flex items-center gap-2 mb-2">
        <AlertTriangle className="w-5 h-5 text-blue-600" />
        <h3 className="text-lg font-bold text-slate-900">Disruption Center</h3>
      </div>
      <p className="text-xs text-slate-500 mb-5">Simulate unexpected travel issues and test deterministic replanning.</p>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 mb-5">
        {DISRUPTION_TYPES.map((d) => (
          <button
            key={d.type}
            onClick={() => setSelectedType(d.type)}
            className={`flex flex-col text-left p-3 rounded-lg border transition-all ${
              selectedType === d.type 
                ? 'border-blue-600 bg-blue-50/60 shadow-sm' 
                : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
            }`}
          >
            <div className="flex items-center gap-2 text-xs font-bold text-slate-900 mb-1">
              {d.icon}
              {d.label}
            </div>
            <span className="text-[11px] text-slate-500 leading-tight">{d.desc}</span>
          </button>
        ))}
      </div>

      {selectedType === 'BUDGET_REDUCTION' && (
        <div className="mb-5 bg-slate-50 p-3.5 rounded-lg border border-slate-200">
          <label className="block text-xs font-bold text-slate-700 mb-1.5">Reduction Amount (₹)</label>
          <Input 
            type="number" 
            value={reductionAmount} 
            onChange={(e) => setReductionAmount(e.target.value)} 
            placeholder="e.g. 5000"
            className="max-w-[200px] bg-white border-slate-200 text-slate-900 text-xs"
          />
        </div>
      )}

      {error && <div className="text-rose-700 text-xs mb-4 p-3 bg-rose-50 border border-rose-200 rounded-lg">{error}</div>}
      
      <div title={!tripId ? "Please load a valid trip first." : ""}>
        <Button 
          onClick={handleTrigger} 
          disabled={loading || !tripId} 
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 shadow-sm text-xs"
        >
          {loading ? 'Finding Feasible Alternatives...' : 'Trigger Disruption & Replan'}
        </Button>
      </div>
    </div>
  );
}
