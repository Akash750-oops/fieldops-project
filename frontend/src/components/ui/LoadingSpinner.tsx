import React from "react";

interface LoadingSpinnerProps {
  message?: string;
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ message = "Loading..." }) => {
  const containerStyle: React.CSSProperties = {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    padding: "40px 24px",
    width: "100%",
  };

  const spinnerStyle: React.CSSProperties = {
    width: "34px",
    height: "34px",
    border: "3px solid #E3ECE7",
    borderTopColor: "#7AAE8A",
    borderRadius: "50%",
    animation: "spin-loader 0.75s cubic-bezier(0.4, 0, 0.2, 1) infinite",
    marginBottom: "12px",
  };

  const textStyle: React.CSSProperties = {
    fontSize: "13px",
    fontWeight: 500,
    color: "#6B7280",
    margin: 0,
  };

  const keyframes = `
    @keyframes spin-loader {
      to { transform: rotate(360deg); }
    }
  `;

  return (
    <div style={containerStyle} className="loading-spinner-container">
      <style>{keyframes}</style>
      <div style={spinnerStyle} className="spinner"></div>
      {message && <p style={textStyle} className="loading-text">{message}</p>}
    </div>
  );
};

export default LoadingSpinner;
