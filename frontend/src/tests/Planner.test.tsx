import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import PlannerPage from '../pages/PlannerPage';
import * as tripsApi from '../api/trips';
import * as destsApi from '../api/destinations';

vi.mock('../api/trips', () => ({
  planTrip: vi.fn(),
}));

vi.mock('../api/destinations', () => ({
  getDestinations: vi.fn().mockResolvedValue([
    { id: 'dest1', name: 'Hyderabad', description: 'City of Pearls', country: 'India', regions: ['South India'], state_province: 'Telangana', latitude: 17, longitude: 78, popular_season: 'Winter', type: 'City' },
    { id: 'dest2', name: 'Goa', description: 'Beaches', country: 'India', regions: ['West India'], state_province: 'Goa', latitude: 15, longitude: 74, popular_season: 'Winter', type: 'State' }
  ]),
  getDestinationCulture: vi.fn().mockResolvedValue({}),
  getDestinationDetails: vi.fn().mockResolvedValue({})
}));


// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('Planner', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('PlannerPage renders and trip planning submission calls the expected API', async () => {
    render(
      <MemoryRouter>
        <PlannerPage />
      </MemoryRouter>
    );
    
    // 1. Planner renders the new title
    expect(screen.getByText(/Intelligent Trip Planning/i)).toBeInTheDocument();
    
    // Wait for destinations to load
    await waitFor(() => {
      expect(screen.getAllByText(/Hyderabad/i).length).toBeGreaterThan(0);
    });


    // 5. Multi-city mode can be enabled
    const multiCityBtn = screen.getByRole('button', { name: /Multi-City/i });
    fireEvent.click(multiCityBtn);

    // 6. A second destination can be added
    const addDestBtn = screen.getByRole('button', { name: /Add another destination/i });
    fireEvent.click(addDestBtn);

    // Select destinations
    const selects = screen.getAllByRole('combobox').slice(0, 2);
    expect(selects.length).toBe(2);
    fireEvent.change(selects[0], { target: { value: 'Hyderabad' } });
    fireEvent.change(selects[1], { target: { value: 'Goa' } });

    // 4. Interests can be selected (History and Food are default, let's select Beaches)
    const beachesBtn = screen.getByRole('button', { name: /Beaches/i });
    fireEvent.click(beachesBtn);

    // Mock successful planning
    const mockPlanTrip = vi.mocked(tripsApi.planTrip).mockResolvedValueOnce({
      id: 'trip-123'
    } as any);

    // 7. Submit form using the new payload
    const submitBtn = screen.getByRole('button', { name: /Generate Trip Plan/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(mockPlanTrip).toHaveBeenCalled();
    });
    
    // Verify multi-city payload structure
    const callArgs = mockPlanTrip.mock.calls[0][0];
    expect(callArgs.destinations).toEqual(['Hyderabad', 'Goa']);
    expect(callArgs.interests).toContain('Beaches');

    // Navigate called
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/trip/trip-123');
    });
  });
});
