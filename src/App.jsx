import JobCreationForm from "./components/JobCreationForm";
import TechnicianList from "./components/TechnicianList";
import "./App.css";

function App() {
  return (
    <div className="app-container">
      <TechnicianList />
      <JobCreationForm />
    </div>
  );
}

export default App;