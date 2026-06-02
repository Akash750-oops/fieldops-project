import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import React from "react";
import "@testing-library/jest-dom";
import ReDispatchHistory from "./ReDispatchHistory";

// Mock global fetch
const mockHistoryData = [
  {
    id: 1,
    job_id: 101,
    attempt_number: 1,
    technician_name: "Rajesh Kumar",
    event_type: "rejection",
    reason: "Location too far",
    queue_position: 3,
    next_dispatch_eta: "2026-06-02T13:15:00Z",
    created_at: "2026-06-02T12:00:00Z"
  },
  {
    id: 2,
    job_id: 101,
    attempt_number: 2,
    technician_name: "Priya Sharma",
    event_type: "timeout",
    reason: "No response",
    queue_position: 2,
    next_dispatch_eta: "2026-06-02T13:20:00Z",
    created_at: "2026-06-02T12:05:00Z"
  }
];

const mockTechs = [
  { technician_id: 1, technician_name: "Rajesh Kumar", technician_skill: "HVAC" },
  { technician_id: 2, technician_name: "Priya Sharma", technician_skill: "Electrical" }
];

describe("ReDispatchHistory Component", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockHistoryData)
      })
    ));
    // Mock AudioContext to prevent errors
    vi.stubGlobal("AudioContext", vi.fn().mockImplementation(() => ({
      createOscillator: () => ({
        connect: () => {},
        frequency: { setValueAtTime: () => {} },
        type: "",
        start: () => {},
        stop: () => {}
      }),
      createGain: () => ({
        connect: () => {},
        gain: { setValueAtTime: () => {}, exponentialRampToValueAtTime: () => {} }
      }),
      destination: {},
      currentTime: 0
    })));
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders headers and loads re-dispatch history statistics correctly", async () => {
    render(
      <ReDispatchHistory
        jobId={101}
        jobTitle="AC Repair"
        onClose={vi.fn()}
        onManualAssign={vi.fn()}
        technicians={mockTechs}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Attempts")).toBeInTheDocument();
    });

    // Check stats badges
    expect(screen.getByText("2")).toBeInTheDocument(); // attempt count
    expect(screen.getAllByText("#2").length).toBeGreaterThanOrEqual(1); // queue position
  });

  it("displays re-dispatch timeline attempts correctly in the table", async () => {
    render(
      <ReDispatchHistory
        jobId={101}
        jobTitle="AC Repair"
        onClose={vi.fn()}
        onManualAssign={vi.fn()}
        technicians={mockTechs}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Location too far")).toBeInTheDocument();
      expect(screen.getByText("No response")).toBeInTheDocument();
      expect(screen.getByText("Rajesh Kumar")).toBeInTheDocument();
      expect(screen.getByText("Priya Sharma")).toBeInTheDocument();
    });
  });

  it("filters timeline entries by event type / reason dropdown selection", async () => {
    render(
      <ReDispatchHistory
        jobId={101}
        jobTitle="AC Repair"
        onClose={vi.fn()}
        onManualAssign={vi.fn()}
        technicians={mockTechs}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Location too far")).toBeInTheDocument();
    });

    const select = screen.getByLabelText("Filter events by type");
    fireEvent.change(select, { target: { value: "timeout" } });

    expect(screen.queryByText("Location too far")).not.toBeInTheDocument();
    expect(screen.getByText("No response")).toBeInTheDocument();
  });

  it("allows dispatcher to force-assign a technician manually", async () => {
    const handleManualAssign = vi.fn().mockResolvedValue({});
    const handleClose = vi.fn();

    render(
      <ReDispatchHistory
        jobId={101}
        jobTitle="AC Repair"
        onClose={handleClose}
        onManualAssign={handleManualAssign}
        technicians={mockTechs}
      />
    );

    await waitFor(() => {
      expect(screen.getByLabelText("Select Technician to Force-Assign")).toBeInTheDocument();
    });

    const select = screen.getByLabelText("Select Technician to Force-Assign");
    fireEvent.change(select, { target: { value: "2" } });

    const submitBtn = screen.getByRole("button", { name: "Manual Assign" });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(handleManualAssign).toHaveBeenCalledWith(101, 2);
      expect(handleClose).toHaveBeenCalled();
    });
  });

  it("triggers CSV download when Export button is clicked", async () => {
    const createObjectURL = vi.fn();
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
    
    // Mock anchor element download clicks
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    render(
      <ReDispatchHistory
        jobId={101}
        jobTitle="AC Repair"
        onClose={vi.fn()}
        onManualAssign={vi.fn()}
        technicians={mockTechs}
      />
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Export history to CSV" })).toBeInTheDocument();
    });

    const exportBtn = screen.getByRole("button", { name: "Export history to CSV" });
    fireEvent.click(exportBtn);

    expect(clickSpy).toHaveBeenCalled();
  });
});
