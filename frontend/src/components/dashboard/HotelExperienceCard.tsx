import React, { useState, useEffect } from 'react';
import { Building2, Star, MapPin, RefreshCw, Check, AlertCircle } from 'lucide-react';
import { Card, CardContent } from '../common/Card';
import { Button } from '../common/Button';
import { updateHotel } from '../../api/trips';
import { getDestinationDetails } from '../../api/destinations';
import type { TripDetailResponse } from '../../types';

interface HotelExperienceCardProps {
  trip: TripDetailResponse;
  onTripUpdated: () => void;
}

export const HotelExperienceCard: React.FC<HotelExperienceCardProps> = ({ trip, onTripUpdated }) => {
  const [selectedStop, setSelectedStop] = useState<any>(trip.stops[0] || null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [destHotels, setDestHotels] = useState<any[]>([]);
  const [fetchingHotels, setFetchingHotels] = useState(false);
  const [updating, setUpdating] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (trip.stops && trip.stops.length > 0 && !selectedStop) {
      setSelectedStop(trip.stops[0]);
    }
  }, [trip]);

  const openChangeModal = async (stop: any) => {
    setSelectedStop(stop);
    setIsModalOpen(true);
    setFetchingHotels(true);
    setError(null);
    try {
      const details = await getDestinationDetails(stop.destination_id);
      setDestHotels(details.hotels || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load hotels');
    } finally {
      setFetchingHotels(false);
    }
  };

  const handleSelectHotel = async (hotelId: string) => {
    if (!selectedStop) return;
    setUpdating(hotelId);
    setError(null);
    try {
      await updateHotel(trip.id, hotelId, selectedStop.id);
      onTripUpdated();
      setIsModalOpen(false);
    } catch (err: any) {
      setError(err.message || 'Failed to update hotel');
    } finally {
      setUpdating(null);
    }
  };

  if (!trip.stops || trip.stops.length === 0) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
          <Building2 className="w-5 h-5 text-blue-600" />
          Accommodations & Stays
        </h3>
        <span className="text-xs text-slate-500 bg-slate-100 px-3 py-1 rounded-full border border-slate-200">
          Deterministic Travel Buffer Optimised
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {trip.stops.map((stop: any) => {
          const hotel = stop.hotel;
          return (
            <Card key={stop.id} className="bg-white border-slate-200 shadow-sm hover:border-blue-300 transition-all">
              <CardContent className="p-5 flex flex-col justify-between h-full space-y-4">
                <div>
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-xs font-bold px-2.5 py-1 rounded-md bg-blue-50 text-blue-700 border border-blue-200">
                      {stop.destination_name}
                    </span>
                    <span className="text-xs text-amber-600 font-semibold flex items-center gap-1">
                      <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                      {hotel?.rating || '4.5'}
                    </span>
                  </div>

                  <h4 className="text-base font-bold text-slate-900 line-clamp-1">
                    {hotel?.name || 'Selected Stay'}
                  </h4>

                  <p className="text-xs text-slate-500 mt-1 flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5 text-slate-400" />
                    {hotel?.address || hotel?.location || `${stop.destination_name} Central District`}
                  </p>

                  <div className="mt-3 flex flex-wrap gap-2 text-xs">
                    {hotel?.price_per_night && (
                      <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-mono font-medium">
                        ₹{hotel.price_per_night.toLocaleString()}/night
                      </span>
                    )}
                    {hotel?.tier && (
                      <span className="bg-blue-50 text-blue-700 border border-blue-100 px-2 py-0.5 rounded capitalize">
                        {hotel.tier} Tier
                      </span>
                    )}
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                  <span className="text-xs text-emerald-700 font-medium flex items-center gap-1">
                    <Check className="w-3.5 h-3.5 text-emerald-600" />
                    Buffer verified
                  </span>
                  <Button
                    variant="outline"
                    className="text-xs py-1 px-3 border-slate-200 text-blue-600 hover:bg-blue-50 hover:border-blue-300"
                    onClick={() => openChangeModal(stop)}
                  >
                    <RefreshCw className="w-3 h-3 mr-1" /> Change Stay
                  </Button>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Change Hotel Modal */}
      {isModalOpen && selectedStop && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-2xl max-w-2xl w-full max-h-[85vh] flex flex-col shadow-xl overflow-hidden animate-in fade-in duration-150">
            <div className="p-5 border-b border-slate-200 flex justify-between items-center bg-slate-50">
              <div>
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <Building2 className="w-5 h-5 text-blue-600" />
                  Select Stay for {selectedStop.destination_name}
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Changing stays automatically recalculates daily travel buffers and morning transfers.
                </p>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-700 text-xl font-bold px-2"
              >
                ✕
              </button>
            </div>

            <div className="p-5 overflow-y-auto space-y-4 flex-1">
              {error && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  {error}
                </div>
              )}

              {fetchingHotels ? (
                <div className="py-12 text-center text-slate-500 animate-pulse flex items-center justify-center gap-2 text-xs font-medium">
                  <RefreshCw className="w-4 h-4 animate-spin text-blue-600" />
                  Loading stays for {selectedStop.destination_name}...
                </div>
              ) : destHotels.length === 0 ? (
                <div className="py-8 text-center text-slate-500 text-xs">
                  No alternative hotels found for this destination.
                </div>
              ) : (
                <div className="space-y-3">
                  {destHotels.map((h: any) => {
                    const isSelected = selectedStop.hotel?.id === h.id;
                    return (
                      <div
                        key={h.id}
                        className={`p-4 rounded-xl border transition-all flex justify-between items-center ${
                          isSelected
                            ? 'bg-blue-50 border-blue-300 text-slate-900'
                            : 'bg-white border-slate-200 text-slate-800 hover:border-blue-200'
                        }`}
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-slate-900">{h.name}</span>
                            <span className="text-xs text-amber-600 font-semibold flex items-center gap-0.5">
                              <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                              {h.rating}
                            </span>
                            {isSelected && (
                              <span className="text-[10px] bg-blue-600 text-white font-bold px-2 py-0.5 rounded-full">
                                Current
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-slate-500">{h.address || h.location || 'Central Location'}</p>
                          <div className="flex gap-2 text-xs pt-1">
                            <span className="font-mono text-slate-700 font-semibold">₹{h.price_per_night?.toLocaleString()}/night</span>
                            <span className="text-slate-300">•</span>
                            <span className="text-slate-500 capitalize">{h.tier} Tier</span>
                          </div>
                        </div>

                        <Button
                          disabled={isSelected || updating === h.id}
                          onClick={() => handleSelectHotel(h.id)}
                          className={`text-xs px-4 py-2 ${
                            isSelected
                              ? 'bg-blue-100 text-blue-800 border border-blue-200 cursor-default shadow-none'
                              : 'bg-blue-600 hover:bg-blue-700 text-white'
                          }`}
                        >
                          {updating === h.id ? (
                            <RefreshCw className="w-4 h-4 animate-spin" />
                          ) : isSelected ? (
                            'Selected'
                          ) : (
                            'Select Stay'
                          )}
                        </Button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
