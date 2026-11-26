import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import MockInterview from "../MockInterview";

const post = vi.fn();

vi.mock("../../contexts/AuthContext", () => ({ useAuth: () => ({ user: { id: "u1" } }) }));
vi.mock("../../api/client", () => ({ api: { post: (...args) => post(...args) } }));
vi.mock("react-router-dom", () => ({ useNavigate: () => vi.fn() }));

describe("MockInterview canonical flow", () => {
  beforeEach(() => {
    localStorage.clear();
    post.mockReset();
  });

  it("persists a device id and sends it on start", async () => {
    post.mockResolvedValueOnce({
      data: {
        session_id: "s1",
        question: "Tell me about a problem you solved.",
        interviewer_message: "Tell me about a problem you solved.",
        status: "in_progress",
      },
    });
    render(<MockInterview />);
    await userEvent.click(screen.getByRole("button", { name: /start interview/i }));
    await waitFor(() => expect(post).toHaveBeenCalled());
    const [url, payload] = post.mock.calls[0];
    expect(url).toBe("/agent-interview/start");
    expect(payload.device_id).toBeTruthy();
    expect(localStorage.getItem("interview_device_id")).toBe(payload.device_id);
    expect(payload.request_id).toBeTruthy();
    expect(localStorage.getItem("interview_session_id")).toBe("s1");
  });

  it("renders competency reasons and no overall score", async () => {
    post
      .mockResolvedValueOnce({
        data: { session_id: "s1", question: "Q1", interviewer_message: "Q1", status: "in_progress" },
      })
      .mockResolvedValueOnce({
        data: { session_id: "s1", status: "completed", report_id: "r1", report_status: "ready", next_question: null },
      })
      .mockResolvedValueOnce({
        data: {
          report_id: "r1",
          outcome: "ready",
          body: {
            report_id: "r1",
            narrative: "Ownership was demonstrated.",
            competencies: [
              { competency: "ownership", level: "strong", confidence: "high",
                reasons: ["Owned the migration end to end."] },
            ],
          },
        },
      });
    render(<MockInterview />);
    await userEvent.click(screen.getByRole("button", { name: /start interview/i }));
    await userEvent.type(screen.getByPlaceholderText(/type your answer/i), "I led the migration and cut errors.");
    await userEvent.click(screen.getByRole("button", { name: /submit/i }));
    await waitFor(() => expect(screen.getByText(/Owned the migration end to end/i)).toBeInTheDocument());
    expect(screen.queryByText(/overall score/i)).not.toBeInTheDocument();
  });

  it("resumes an existing session with the stored device id", async () => {
    localStorage.setItem("interview_device_id", "device-existing");
    post
      .mockRejectedValueOnce({ response: { status: 409, data: { detail: { code: "session_exists" } } } })
      .mockResolvedValueOnce({
        data: { session_id: "s1", question: "Q1", status: "in_progress", device_id: "device-existing" },
      });
    render(<MockInterview />);
    await userEvent.click(screen.getByRole("button", { name: /start interview/i }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(2));
    expect(post.mock.calls[1][0]).toBe("/agent-interview/resume");
    expect(post.mock.calls[1][1].device_id).toBe("device-existing");
  });

  it("resumes the persisted session after device_conflict", async () => {
    localStorage.setItem("interview_session_id", "s1");
    post
      .mockRejectedValueOnce({ response: { status: 409, data: { detail: { code: "device_conflict" } } } })
      .mockResolvedValueOnce({
        data: { session_id: "s1", question: "Q1", interviewer_message: "Q1", status: "in_progress" },
      });
    render(<MockInterview />);
    await userEvent.click(screen.getByRole("button", { name: /start interview/i }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(2));
    expect(post.mock.calls[1][0]).toBe("/agent-interview/resume");
    expect(post.mock.calls[1][1].session_id).toBe("s1");
    expect(post.mock.calls[1][1].device_id).toBeTruthy();
  });

  it("shows a preparing state while a pending answer is polled", async () => {
    post
      .mockResolvedValueOnce({
        data: { session_id: "s1", question: "Q1", interviewer_message: "Q1", status: "in_progress" },
      })
      .mockResolvedValueOnce({ status: 202, data: { question_pending: true } })
      .mockResolvedValueOnce({
        data: { session_id: "s1", status: "in_progress", next_question: "Q2", question_pending: false },
      });
    render(<MockInterview />);
    await userEvent.click(screen.getByRole("button", { name: /start interview/i }));
    await userEvent.type(screen.getByPlaceholderText(/type your answer/i), "I owned the migration and cut errors.");
    await userEvent.click(screen.getByRole("button", { name: /submit/i }));
    await waitFor(() => expect(screen.getByText(/preparing your next question/i)).toBeInTheDocument());
    await waitFor(() => expect(screen.queryByText(/preparing your next question/i)).not.toBeInTheDocument());
  });
});
