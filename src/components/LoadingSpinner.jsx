import React from "react";
import "./LoadingSpinner.css";

const LoadingSpinner = ({ message = "Loading..." }) => {
  return (
    <div className="loading-spinner-container">
      <div className="spinner"></div>
      {message && <p className="loading-text">{message}</p>}
    </div>
  );
};

export default LoadingSpinner;
