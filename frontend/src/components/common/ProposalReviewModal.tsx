import { Check, X, ArrowRight, IndianRupee, Clock, MapPin, AlertCircle, PlusCircle, Trash2, Edit3 } from 'lucide-react';
import { Button } from './Button';
import type { ProposedReplan, WhatIfSimulationResult, ItemModification } from '../../types';

interface ProposalReviewModalProps {
  proposal: ProposedReplan | WhatIfSimulationResult;
  type: 'replan' | 'simulation';
  onApply: (id: string, type: 'replan' | 'simulation') => void;
  onReject: (id: string, type: 'replan' | 'simulation') => void;
}

export function ProposalReviewModal({ proposal, type, onApply, onReject }: ProposalReviewModalProps) {
  const isSimulation = type === 'simulation';
  const id = isSimulation ? (proposal as WhatIfSimulationResult).simulation_id : (proposal as ProposedReplan).replan_id;
  
  const diff = proposal.diff;
  
  // Format currency
  const formatMoney = (amount: number) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/50 backdrop-blur-sm overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
        
        {/* Header */}
        <div className={`px-6 py-4 border-b ${isSimulation ? 'bg-blue-600' : 'bg-red-600'} text-white flex justify-between items-center`}>
          <div>
            <h2 className="text-xl font-bold flex items-center gap-2">
              {isSimulation ? 'Review What-If Simulation' : 'Review Disruption Replan'}
              {!proposal.feasible && <span className="bg-red-800 text-xs px-2 py-1 rounded-full flex items-center gap-1"><AlertCircle className="w-3 h-3"/> Infeasible</span>}
            </h2>
            <p className="text-sm opacity-90">
              {isSimulation 
                ? `Simulation Type: ${(proposal as WhatIfSimulationResult).type}`
                : `Disruption Handled: ${(proposal as ProposedReplan).disruption_type}`
              }
            </p>
          </div>
          <button onClick={() => onReject(id || '', type)} className="p-2 hover:bg-white/20 rounded-full transition-colors">
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 bg-gray-50">
          
          {/* Summary Banner */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 mb-6 flex flex-wrap gap-6 items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-gray-100 rounded-lg">
                <IndianRupee className="w-6 h-6 text-gray-700" />
              </div>
              <div>
                <p className="text-sm text-gray-500 font-medium">Budget Impact</p>
                <div className="flex items-center gap-2">
                  <span className="text-gray-400 line-through text-sm">{formatMoney(diff.budget_before)}</span>
                  <ArrowRight className="w-4 h-4 text-gray-400" />
                  <span className={`text-lg font-bold ${diff.budget_delta < 0 ? 'text-green-600' : diff.budget_delta > 0 ? 'text-red-600' : 'text-gray-900'}`}>
                    {formatMoney(diff.budget_after)}
                  </span>
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${diff.budget_delta < 0 ? 'bg-green-100 text-green-700' : diff.budget_delta > 0 ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-700'}`}>
                    {diff.budget_delta > 0 ? '+' : ''}{formatMoney(diff.budget_delta)}
                  </span>
                </div>
              </div>
            </div>
            
            <div className="text-right">
              <p className="text-sm text-gray-500 mb-1">{isSimulation ? 'Simulation Note' : 'Agent Summary'}</p>
              <p className="text-sm font-medium text-gray-900 max-w-md">
                {isSimulation ? diff.summary : (proposal as ProposedReplan).summary || diff.summary}
              </p>
            </div>
          </div>

          {/* Validation Warnings */}
          {((proposal as any).warnings?.length > 0 || !(proposal as any).feasible) && (
            <div className="bg-orange-50 border-l-4 border-orange-500 p-4 mb-6 rounded-r-lg">
              <h4 className="flex items-center text-orange-800 font-bold mb-2">
                <AlertCircle className="w-5 h-5 mr-2" />
                Validation Warnings
              </h4>
              <ul className="list-disc list-inside text-sm text-orange-700 space-y-1">
                {!(proposal as any).feasible && <li>The proposed itinerary is structurally invalid.</li>}
                {(proposal as any).warnings?.map((w: string, i: number) => <li key={i}>{w}</li>)}
                {(proposal as any).errors?.map((e: string, i: number) => <li key={i} className="text-red-600">{e}</li>)}
              </ul>
            </div>
          )}

          {/* Diff Lists */}
          <div className="space-y-6">
            
            {/* Removed Items */}
            {(diff.removed_items || []).length > 0 && (
              <div>
                <h4 className="font-bold text-gray-800 mb-3 flex items-center gap-2 border-b pb-2">
                  <Trash2 className="w-5 h-5 text-red-500" /> Removed Activities
                </h4>
                <div className="grid gap-3">
                  {(diff.removed_items || []).map((item: any, i: number) => (
                    <div key={i} className="bg-red-50 border border-red-100 rounded-lg p-3 flex justify-between items-center line-through opacity-75">
                      <div>
                        <p className="font-semibold text-red-900">{item.custom_title || item.title || 'Activity'}</p>
                        <p className="text-xs text-red-700">{item.scheduled_date} • {item.start_time} - {item.end_time}</p>
                      </div>
                      <span className="text-sm font-medium text-red-800">-{formatMoney(item.cost)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Added Items */}
            {(diff.added_items || []).length > 0 && (
              <div>
                <h4 className="font-bold text-gray-800 mb-3 flex items-center gap-2 border-b pb-2">
                  <PlusCircle className="w-5 h-5 text-green-500" /> Added Alternatives
                </h4>
                <div className="grid gap-3">
                  {(diff.added_items || []).map((item: any, i: number) => (
                    <div key={i} className="bg-green-50 border border-green-200 rounded-lg p-3 flex justify-between items-center shadow-sm">
                      <div>
                        <p className="font-bold text-green-900">{item.custom_title || item.title || 'Activity'}</p>
                        <p className="text-xs text-green-700 font-medium flex items-center gap-1">
                          <Clock className="w-3 h-3"/> {item.scheduled_date} • {item.start_time} - {item.end_time}
                        </p>
                      </div>
                      <span className="text-sm font-bold text-green-700">+{formatMoney(item.cost)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Modified Items */}
            {(diff.modified_items || []).length > 0 && (
              <div>
                <h4 className="font-bold text-gray-800 mb-3 flex items-center gap-2 border-b pb-2">
                  <Edit3 className="w-5 h-5 text-blue-500" /> Modified Items
                </h4>
                <div className="grid gap-3">
                  {(diff.modified_items || []).map((mod: ItemModification, i: number) => (
                    <div key={i} className="bg-blue-50 border border-blue-100 rounded-lg p-3 shadow-sm">
                      <p className="font-semibold text-blue-900 mb-2">{mod.title || 'Item Modified'}</p>
                      <div className="space-y-1">
                        {Object.entries(mod.field_changes).map(([field, change]) => (
                          <div key={field} className="text-sm flex items-center gap-2 text-blue-800">
                            <span className="font-medium capitalize w-20">{field.replace('_', ' ')}:</span>
                            <span className="line-through opacity-75">{String(change.before)}</span>
                            <ArrowRight className="w-3 h-3" />
                            <span className="font-bold">{String(change.after)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* If no visible changes (edge case) */}
            {(diff.added_items || []).length === 0 && (diff.removed_items || []).length === 0 && (diff.modified_items || []).length === 0 && (
              <div className="text-center py-8 text-gray-500 bg-white rounded-xl border border-gray-200">
                <MapPin className="w-8 h-8 mx-auto text-gray-400 mb-2" />
                <p>No itinerary items were added, removed, or modified.</p>
                <p className="text-xs mt-1">Budget or top-level properties might have changed.</p>
              </div>
            )}

          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 border-t bg-white flex justify-end gap-3">
          <Button variant="outline" onClick={() => onReject(id || '', type)}>
            Reject Changes
          </Button>
          <Button 
            className={`${isSimulation ? 'bg-blue-600 hover:bg-blue-700' : 'bg-red-600 hover:bg-red-700'}`}
            onClick={() => onApply(id || '', type)}
          >
            <Check className="w-4 h-4 mr-2" />
            Apply Changes
          </Button>
        </div>
      </div>
    </div>
  );
}
