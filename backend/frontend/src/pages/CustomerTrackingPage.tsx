import React, { useEffect, useRef } from 'react';
import { useCustomerTrackingStore } from '../store/customerTrackingStore';
import { GoogleMap, useJsApiLoader, MarkerF } from '@react-google-maps/api';
import { QRCodeSVG } from 'qrcode.react';
import { MapPin, Clock, Star, Phone, CheckCircle, ShieldAlert, Navigation } from 'lucide-react';

interface CustomerTrackingPageProps {
  token: string;
}

const mapContainerStyle = {
  width: '100%',
  height: '100%',
};

export const CustomerTrackingPage: React.FC<CustomerTrackingPageProps> = ({ token }) => {
  const {
    job,
    technician,
    latestGps,
    eta,
    expired,
    loading,
    error,
    fetchTrackingInfo
  } = useCustomerTrackingStore();

  const isLoadedRef = useRef(false);

  // Load Google Maps API Key
  const { isLoaded } = useJsApiLoader({
    id: 'google-map-script',
    googleMapsApiKey: (window as any).VITE_GOOGLE_MAPS_API_KEY || (import.meta as any).env?.VITE_GOOGLE_MAPS_API_KEY || '',
  });

  // Setup SEO and document properties
  useEffect(() => {
    document.title = 'Track Your Service - FieldOps';
    
    // Add meta noindex tag dynamically
    const meta = document.createElement('meta');
    meta.name = 'robots';
    meta.content = 'noindex, nofollow';
    document.head.appendChild(meta);

    return () => {
      document.head.removeChild(meta);
    };
  }, []);

  // Fetch tracking info initially and poll every 30 seconds
  useEffect(() => {
    fetchTrackingInfo(token);
    const interval = setInterval(() => {
      fetchTrackingInfo(token);
    }, 30000);

    return () => clearInterval(interval);
  }, [token, fetchTrackingInfo]);

  // Center coordinate resolver
  const getMapCenter = () => {
    if (latestGps && latestGps.latitude && latestGps.longitude) {
      return { lat: latestGps.latitude, lng: latestGps.longitude };
    }
    if (job && job.site_latitude && job.site_longitude) {
      return { lat: job.site_latitude, lng: job.site_longitude };
    }
    return { lat: 13.0827, lng: 80.2707 }; // Chennai fallback
  };

  const mapCenter = getMapCenter();

  // Helper to format status text nicely
  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'ASSIGNED':
        return 'Technician Assigned';
      case 'EN_ROUTE':
        return 'En Route (On the Way)';
      case 'ON_SITE':
        return 'On Site (Working)';
      case 'COMPLETED':
        return 'Service Complete';
      default:
        return status;
    }
  };

  // Helper for status badge colors
  const getStatusBadgeStyle = (status: string) => {
    switch (status) {
      case 'ASSIGNED':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'EN_ROUTE':
        return 'bg-amber-100 text-amber-800 border-amber-200 animate-pulse';
      case 'ON_SITE':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200';
      case 'COMPLETED':
        return 'bg-slate-100 text-slate-800 border-slate-200';
      default:
        return 'bg-slate-100 text-slate-700';
    }
  };

  // Loading state
  if (loading && !job) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center font-sans">
        <div className="text-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-emerald-600 mx-auto"></div>
          <p className="text-slate-500 font-medium">Securing tracking connection...</p>
        </div>
      </div>
    );
  }

  // Expired state
  if (expired) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4 font-sans select-none">
        <div className="bg-white max-w-md w-full rounded-2xl shadow-xl border border-slate-200 p-8 text-center space-y-6">
          <div className="bg-rose-100 text-rose-600 h-16 w-16 rounded-full flex items-center justify-center mx-auto">
            <ShieldAlert size={36} />
          </div>
          <div className="space-y-2">
            <h1 className="text-xl font-bold text-slate-900">Tracking Link Expired</h1>
            <p className="text-slate-500 text-sm">
              For your safety and security, live tracking links automatically expire 24 hours after generation or once the service is closed.
            </p>
          </div>
          <div className="pt-4 border-t border-slate-100 space-y-3">
            <p className="text-xs text-slate-400">Need assistance or want to reschedule?</p>
            <a
              href="tel:18005550199"
              className="inline-flex items-center justify-center gap-2 w-full bg-slate-900 hover:bg-slate-800 text-white font-semibold py-3 px-4 rounded-xl transition duration-200 shadow-md cursor-pointer"
            >
              <Phone size={18} />
              Contact Customer Support
            </a>
          </div>
        </div>
      </div>
    );
  }

  // Completed state
  if (job?.status === 'COMPLETED') {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4 font-sans select-none">
        <div className="bg-white max-w-md w-full rounded-2xl shadow-xl border border-slate-200 p-8 text-center space-y-6">
          <div className="bg-emerald-100 text-emerald-600 h-16 w-16 rounded-full flex items-center justify-center mx-auto">
            <CheckCircle size={36} />
          </div>
          <div className="space-y-2">
            <h1 className="text-xl font-bold text-slate-900">Service Completed!</h1>
            <p className="text-slate-500 text-sm">
              Your technician, {technician?.name || 'field agent'}, has completed the work. Thank you for choosing FieldOps!
            </p>
          </div>

          <div className="bg-emerald-50/50 rounded-xl p-4 border border-emerald-100/50 space-y-3">
            <p className="text-sm font-semibold text-emerald-950">How was your service?</p>
            <div className="flex justify-center gap-2">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  className="text-amber-400 hover:scale-115 transition duration-150 cursor-pointer"
                >
                  <Star size={24} fill="currentColor" />
                </button>
              ))}
            </div>
          </div>

          <div className="pt-4 border-t border-slate-100">
            <a
              href="#"
              className="inline-flex items-center justify-center w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-3 px-4 rounded-xl transition duration-200 shadow-md cursor-pointer"
            >
              Submit Feedback Survey
            </a>
          </div>
        </div>
      </div>
    );
  }

  // Standard tracking view
  return (
    <div className="flex flex-col h-screen bg-slate-50 font-sans overflow-hidden md:flex-row">
      {/* Sidebar Details Panel */}
      <div className="w-full md:w-[400px] bg-white border-b md:border-b-0 md:border-r border-slate-200 flex flex-col z-10 shadow-lg md:h-full overflow-y-auto">
        {/* Header branding */}
        <div className="px-6 py-5 border-b border-slate-100 flex justify-between items-center bg-slate-50/80">
          <div>
            <h2 className="text-sm font-bold text-slate-950 tracking-wide uppercase">FieldOps Live Track</h2>
            <p className="text-xs text-slate-500">Live service tracking dashboard</p>
          </div>
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-emerald-100 border border-emerald-200">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-ping"></span>
            <span className="text-[10px] font-bold text-emerald-800 uppercase tracking-wider">Live</span>
          </div>
        </div>

        {/* Dynamic ETA section */}
        <div className="px-6 py-6 border-b border-slate-100 flex flex-col space-y-4">
          <div className="flex items-center gap-3">
            <div className="bg-emerald-100 text-emerald-600 h-10 w-10 rounded-full flex items-center justify-center">
              <Clock size={20} />
            </div>
            <div>
              <p className="text-xs text-slate-500 font-medium">Estimated Arrival</p>
              <h1 className="text-2xl font-bold text-slate-900">
                {eta !== null && eta > 0 ? `Arriving in ${eta} minutes` : 'Calculating ETA...'}
              </h1>
            </div>
          </div>

          <div className="flex items-center justify-between pt-2">
            <span className="text-xs text-slate-500 font-medium">Job Status:</span>
            <span className={`px-2.5 py-1 text-xs font-bold border rounded-full uppercase tracking-wider ${getStatusBadgeStyle(job?.status || '')}`}>
              {getStatusLabel(job?.status || '')}
            </span>
          </div>
        </div>

        {/* Assigned Technician Card */}
        {technician && (
          <div className="px-6 py-6 border-b border-slate-100 space-y-4">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Your Technician</h3>
            <div className="flex items-center justify-between bg-slate-50/50 border border-slate-100 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <div className="bg-emerald-600 text-white h-12 w-12 rounded-full flex items-center justify-center font-bold text-lg shadow-inner">
                  {technician.avatar}
                </div>
                <div>
                  <h4 className="font-bold text-slate-900">{technician.name}</h4>
                  <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium mt-0.5">
                    <Star size={14} className="text-amber-400" fill="currentColor" />
                    <span>{technician.rating} Rating</span>
                  </div>
                </div>
              </div>
              <a
                href={`tel:${job?.contact_number || '18005550199'}`}
                className="bg-white border border-slate-200 hover:bg-slate-50 h-10 w-10 rounded-xl flex items-center justify-center text-slate-700 shadow-sm transition cursor-pointer"
                aria-label="Call support"
              >
                <Phone size={18} />
              </a>
            </div>
          </div>
        )}

        {/* Job details card */}
        {job && (
          <div className="px-6 py-6 border-b border-slate-100 space-y-4 flex-1">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Service Details</h3>
            <div className="space-y-4">
              <div>
                <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Service Type</p>
                <p className="text-sm font-semibold text-slate-800 mt-0.5">{job.service_type}</p>
                <p className="text-xs text-slate-500 mt-0.5">{job.issue_description}</p>
              </div>

              <div className="flex items-start gap-2">
                <MapPin className="text-slate-400 mt-0.5 flex-shrink-0" size={16} />
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Service Address</p>
                  <p className="text-xs text-slate-600 font-medium mt-0.5">{job.site_address}</p>
                </div>
              </div>

              <div>
                <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Scheduled Time Window</p>
                <p className="text-xs text-slate-600 font-medium mt-0.5">{job.scheduled_window}</p>
              </div>
            </div>
          </div>
        )}

        {/* QR Code generator */}
        <div className="px-6 py-6 bg-slate-50/50 border-t border-slate-100 flex items-center gap-4">
          <div className="bg-white p-2 border border-slate-200 rounded-xl flex-shrink-0 shadow-sm">
            <QRCodeSVG value={window.location.href} size={70} />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-900">Track on your mobile device</h4>
            <p className="text-[10px] text-slate-500 font-medium mt-0.5">
              Scan this QR code with your smartphone camera to continue tracking on the go.
            </p>
          </div>
        </div>
      </div>

      {/* Map Container */}
      <div className="flex-1 h-[400px] md:h-full relative bg-slate-200 z-0">
        {isLoaded ? (
          <GoogleMap
            mapContainerStyle={mapContainerStyle}
            center={mapCenter}
            zoom={14}
            options={{
              disableDefaultUI: true, // simplified map, no controls
              gestureHandling: 'none', // locked pan/zoom
              zoomControl: false,
            }}
          >
            {latestGps && latestGps.latitude && latestGps.longitude && (
              <MarkerF
                position={{ lat: latestGps.latitude, lng: latestGps.longitude }}
                icon={{
                  url: 'https://maps.google.com/mapfiles/ms/icons/truck.png',
                  scaledSize: typeof google !== 'undefined' ? new google.maps.Size(40, 40) : undefined,
                }}
              />
            )}
            
            {job && job.site_latitude && job.site_longitude && (
              <MarkerF
                position={{ lat: job.site_latitude, lng: job.site_longitude }}
                icon={{
                  url: 'https://maps.google.com/mapfiles/ms/icons/red-pushpin.png',
                  scaledSize: typeof google !== 'undefined' ? new google.maps.Size(35, 35) : undefined,
                }}
              />
            )}
          </GoogleMap>
        ) : (
          <div className="h-full w-full flex items-center justify-center bg-slate-100">
            <p className="text-slate-400 font-medium flex items-center gap-2">
              <Navigation className="animate-spin" size={18} />
              Loading interactive map...
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default CustomerTrackingPage;
