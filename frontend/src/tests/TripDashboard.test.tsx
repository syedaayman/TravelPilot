import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import TripDashboardPage from '../pages/TripDashboardPage';
import * as tripsApi from '../api/trips';
import * as disruptionsApi from '../api/disruptions';
import * as simulationsApi from '../api/simulations';
import * as agentApi from '../api/agent';

vi.mock('../api/trips');
vi.mock('../api/disruptions');
vi.mock('../api/simulations');
vi.mock('../api/agent');

const mockTrip = {
  id: 'trip-123',
  title: 'My Cool Trip',
  start_date: '2026-09-20',
  end_date: '2026-09-25',
  traveler_count: 2,
  total_budget: 50000,
  stops: [
    {
      id: 'stop-1',
      destination_name: 'Hyderabad',
      stop_budget: 1000
    }
  ],
  itinerary: [
    {
      id: 'item-1',
      trip_stop_id: 'stop-1',
      day_number: 1,
      custom_title: 'Visit Charminar',
      start_time: '10:00',
      end_time: '12:00',
      scheduled_date: '2026-09-21',
      cost: 1000,
      item_type: 'place',
      travel_time_from_prev_minutes: 0
    }
  ],
  transport_legs: []
};

const mockProposal = {
  replan_id: 'replan-1',
  disruption_type: 'VENUE_CLOSED',
  feasible: true,
  summary: 'Swapped Charminar for Golconda Fort',
  diff: {
    budget_before: 50000,
    budget_after: 49000,
    budget_delta: -1000,
    added_items: [],
    removed_items: [],
    modified_items: [],
    summary: 'Saved 1000 INR'
  }
};

const mockSimulation = {
  simulation_id: 'sim-1',
  type: 'BUDGET_CHANGE',
  feasible: true,
  summary: 'Reduced budget by 5000',
  diff: {
    budget_before: 50000,
    budget_after: 45000,
    budget_delta: -5000,
    added_items: [],
    removed_items: [],
    modified_items: [],
    summary: 'Reduced overall budget'
  }
};

describe('Trip Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(tripsApi.getTrip).mockResolvedValue(mockTrip as any);
    vi.mocked(agentApi.getAgentEvents).mockResolvedValue({ success: true, events: [] });
    // Mock window.alert
    vi.spyOn(window, 'alert').mockImplementation(() => {});
  });

  const renderDashboard = () => {
    return render(
      <MemoryRouter initialEntries={['/trip/trip-123']}>
        <Routes>
          <Route path="/trip/:tripId" element={<TripDashboardPage />} />
        </Routes>
      </MemoryRouter>
    );
  };

  it('B. TripDashboardPage renders with representative trip data', async () => {
    renderDashboard();
    expect(screen.getByText(/Loading dashboard/i)).toBeInTheDocument();
    
    await waitFor(() => {
      expect(screen.getByText('My Cool Trip')).toBeInTheDocument();
    });
    
    expect(screen.getAllByText(/Hyderabad/i).length).toBeGreaterThan(0);
    expect(tripsApi.getTrip).toHaveBeenCalledWith('trip-123');
  });

  it('C. Disruption proposal appears and reject leaves trip unchanged', async () => {
    renderDashboard();
    await waitFor(() => expect(screen.getByText('My Cool Trip')).toBeInTheDocument());

    vi.mocked(disruptionsApi.triggerDisruption).mockResolvedValueOnce({
      success: true,
      trip_id: 'trip-123',
      replan_id: 'replan-1',
      disruption_analysis: {} as any,
      diff: mockProposal.diff,
      proposed_replan: mockProposal as any
    });

    const triggerBtn = screen.getByRole('button', { name: /Trigger Disruption & Replan/i });
    fireEvent.click(triggerBtn);

    await waitFor(() => {
      expect(screen.getByText(/Review Disruption Replan/i)).toBeInTheDocument();
    });

    vi.mocked(disruptionsApi.rejectReplan).mockResolvedValueOnce({ success: true });
    
    const rejectBtn = screen.getByRole('button', { name: /Reject Changes/i });
    fireEvent.click(rejectBtn);

    await waitFor(() => {
      expect(disruptionsApi.rejectReplan).toHaveBeenCalledWith('replan-1');
      expect(screen.queryByText(/Review Disruption Replan/i)).not.toBeInTheDocument();
    });
    
    // Active trip remains unchanged (getTrip not called again to fetch new state)
    expect(tripsApi.getTrip).toHaveBeenCalledTimes(1);
  });

  it('D. Disruption apply refreshes the trip and clears proposal', async () => {
    renderDashboard();
    await waitFor(() => expect(screen.getByText('My Cool Trip')).toBeInTheDocument());

    vi.mocked(disruptionsApi.triggerDisruption).mockResolvedValueOnce({
      success: true,
      trip_id: 'trip-123',
      replan_id: 'replan-1',
      disruption_analysis: {} as any,
      diff: mockProposal.diff,
      proposed_replan: mockProposal as any
    });

    fireEvent.click(screen.getByRole('button', { name: /Trigger Disruption & Replan/i }));

    await waitFor(() => expect(screen.getByText(/Review Disruption Replan/i)).toBeInTheDocument());

    vi.mocked(disruptionsApi.applyReplan).mockResolvedValueOnce({ success: true, trip_id: 'trip-123' });
    
    const applyBtn = screen.getByRole('button', { name: /Apply Changes/i });
    fireEvent.click(applyBtn);

    await waitFor(() => {
      expect(disruptionsApi.applyReplan).toHaveBeenCalledWith('replan-1');
      expect(screen.queryByText(/Review Disruption Replan/i)).not.toBeInTheDocument();
      // Fetches trip again to refresh
      expect(tripsApi.getTrip).toHaveBeenCalledTimes(2);
    });
  });

  it('E. What-if simulation renders, reject leaves active trip unchanged, apply refreshes trip', async () => {
    renderDashboard();
    await waitFor(() => expect(screen.getByText('My Cool Trip')).toBeInTheDocument());

    vi.mocked(simulationsApi.triggerSimulation).mockResolvedValueOnce(mockSimulation as any);

    const simBtn = screen.getByRole('button', { name: /Run Simulation/i });
    fireEvent.click(simBtn);

    await waitFor(() => expect(screen.getByText(/Review What-If Simulation/i)).toBeInTheDocument());

    vi.mocked(simulationsApi.rejectSimulation).mockResolvedValueOnce({ success: true });
    
    // Test Reject
    fireEvent.click(screen.getByRole('button', { name: /Reject Changes/i }));

    await waitFor(() => {
      expect(simulationsApi.rejectSimulation).toHaveBeenCalledWith('sim-1');
      expect(screen.queryByText(/Review What-If Simulation/i)).not.toBeInTheDocument();
    });

    expect(tripsApi.getTrip).toHaveBeenCalledTimes(1);

    // Test Apply
    vi.mocked(simulationsApi.triggerSimulation).mockResolvedValueOnce(mockSimulation as any);
    fireEvent.click(screen.getByRole('button', { name: /Run Simulation/i }));
    await waitFor(() => expect(screen.getByText(/Review What-If Simulation/i)).toBeInTheDocument());

    vi.mocked(simulationsApi.applySimulation).mockResolvedValueOnce({ success: true, trip_id: 'trip-123' });
    
    fireEvent.click(screen.getByRole('button', { name: /Apply Changes/i }));

    await waitFor(() => {
      expect(simulationsApi.applySimulation).toHaveBeenCalledWith('sim-1');
      expect(screen.queryByText(/Review What-If Simulation/i)).not.toBeInTheDocument();
      expect(tripsApi.getTrip).toHaveBeenCalledTimes(2);
    });
  });

  it('F. Stale proposal shows message, discards proposal, gives refresh option', async () => {
    renderDashboard();
    await waitFor(() => expect(screen.getByText('My Cool Trip')).toBeInTheDocument());

    vi.mocked(disruptionsApi.triggerDisruption).mockResolvedValueOnce({
      success: true,
      trip_id: 'trip-123',
      replan_id: 'replan-1',
      disruption_analysis: {} as any,
      diff: mockProposal.diff,
      proposed_replan: mockProposal as any
    });

    fireEvent.click(screen.getByRole('button', { name: /Trigger Disruption & Replan/i }));
    await waitFor(() => expect(screen.getByText(/Review Disruption Replan/i)).toBeInTheDocument());

    // Mock 409 error
    const staleError = Object.assign(new Error('Stale Proposal'), { status: 409 });
    vi.mocked(disruptionsApi.applyReplan).mockRejectedValueOnce(staleError);

    fireEvent.click(screen.getByRole('button', { name: /Apply Changes/i }));

    await waitFor(() => {
      expect(disruptionsApi.applyReplan).toHaveBeenCalledWith('replan-1');
      // Alert should be called with stale message
      expect(window.alert).toHaveBeenCalledWith(expect.stringContaining('changed while this proposal was open'));
      // Proposal should be closed/discarded
      expect(screen.queryByText(/Review Disruption Replan/i)).not.toBeInTheDocument();
    });
    
    // UI doesn't automatically apply it since it was rejected
    // The alert message instructs them to refresh the trip.
  });
});
