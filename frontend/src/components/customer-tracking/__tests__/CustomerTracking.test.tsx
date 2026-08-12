import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { CustomerTrackingPage } from '../../../pages/CustomerTrackingPage';
import { useCustomerTrackingStore } from '../../../store/customerTrackingStore';

// Mock Zustand Store
vi.mock('../../../store/customerTrackingStore', () => {
  const store = {
    job: null,
    technician: null,
    latestGps: null,
    eta: null,
    expired: false,
    loading: false,
    error: null,
    fetchTrackingInfo: vi.fn(),
  };
  return {
    useCustomerTrackingStore: () => store,
  };
});

// Mock @react-google-maps/api
vi.mock('@react-google-maps/api', () => ({
  GoogleMap: ({ children }: any) => <div data-testid="mock-google-map">{children}</div>,
  MarkerF: () => <div data-testid="mock-marker" />,
  useJsApiLoader: () => ({ isLoaded: true, loadError: null }),
}));

describe('CustomerTrackingPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders loading spinner when loading is true', () => {
    const store = useCustomerTrackingStore();
    store.loading = true;
    store.job = null;

    render(<CustomerTrackingPage token="test-token" />);

    expect(screen.getByText('Securing tracking connection...')).toBeDefined();
  });

  it('renders expired notice when link is expired', () => {
    const store = useCustomerTrackingStore();
    store.loading = false;
    store.expired = true;
    store.job = null;

    render(<CustomerTrackingPage token="expired-token" />);

    expect(screen.getByText('Tracking Link Expired')).toBeDefined();
    expect(screen.getByText(/links automatically expire 24 hours/)).toBeDefined();
  });

  it('renders service completed view when status is COMPLETED', () => {
    const store = useCustomerTrackingStore();
    store.loading = false;
    store.expired = false;
    store.job = {
      id: '123',
      customer_name: 'Alice',
      issue_description: 'AC broken',
      service_type: 'HVAC Repair',
      status: 'COMPLETED',
      site_latitude: 13.0827,
      site_longitude: 80.2707,
      site_address: '123 Main St',
      scheduled_window: '2:00 PM - 4:00 PM',
    };
    store.technician = {
      name: 'Vijay',
      rating: 4.8,
      avatar: 'V',
    };

    render(<CustomerTrackingPage token="completed-token" />);

    expect(screen.getByText('Service Completed!')).toBeDefined();
    expect(screen.getByText(/has completed the work/)).toBeDefined();
    expect(screen.getByText('How was your service?')).toBeDefined();
  });

  it('renders live tracking dashboard with details and map when active', () => {
    const store = useCustomerTrackingStore();
    store.loading = false;
    store.expired = false;
    store.job = {
      id: '123',
      customer_name: 'Alice',
      issue_description: 'AC check',
      service_type: 'HVAC Maintenance',
      status: 'EN_ROUTE',
      site_latitude: 13.0827,
      site_longitude: 80.2707,
      site_address: '123 Main St',
      scheduled_window: '2:00 PM - 4:00 PM',
    };
    store.technician = {
      name: 'Vijay',
      rating: 4.8,
      avatar: 'V',
    };
    store.latestGps = {
      latitude: 13.0900,
      longitude: 80.2800,
      timestamp: new Date().toISOString(),
    };
    store.eta = 15;

    render(<CustomerTrackingPage token="active-token" />);

    expect(screen.getByText('FieldOps Live Track')).toBeDefined();
    expect(screen.getByText('Arriving in 15 minutes')).toBeDefined();
    expect(screen.getByText('En Route (On the Way)')).toBeDefined();
    expect(screen.getByText('Vijay')).toBeDefined();
    expect(screen.getByText('HVAC Maintenance')).toBeDefined();
    expect(screen.getByText('123 Main St')).toBeDefined();
    expect(screen.getByTestId('mock-google-map')).toBeDefined();
  });
});
