import { useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const SUBJECT_OPTIONS = [
  "biology",
  "computer_science",
  "mathematics",
  "chemistry",
  "physics",
  "design_arts",
  "literature",
  "medicine",
  "finance_economics",
  "management",
  "psychology",
  "history",
  "drama",
  "law",
];

const FIELD_LABELS = {
  biology: "Biology",
  computer_science: "Computer Science",
  mathematics: "Mathematics",
  chemistry: "Chemistry",
  physics: "Physics",
  design_arts: "Design & Arts",
  literature: "Literature",
  medicine: "Medicine",
  finance_economics: "Finance & Economics",
  management: "Management",
  psychology: "Psychology",
  history: "History",
  drama: "Drama",
  law: "Law",
  education: "Education",
  humanities_general: "Humanities (General)",
};

function getFieldLabel(field) {
  return FIELD_LABELS[field] || field.replaceAll("_", " ");
}

function SectionCard({ title, children }) {
  return (
    <div style={{
      background: "#ffffff",
      border: "1px solid #e5e7eb",
      borderRadius: "16px",
      padding: "20px",
      boxShadow: "0 4px 20px rgba(0,0,0,0.04)",
      height: "100%",
      overflow: "auto",
      boxSizing: "border-box",
    }}>
      <h2 style={{ marginTop: 0, marginBottom: "18px", fontSize: "22px" }}>
        {title}
      </h2>
      {children}
    </div>
  );
}

function RadioGroup({ title, name, options, value, onChange }) {
  return (
    <div style={{ marginBottom: "22px" }}>
      <div style={{ fontWeight: "bold", marginBottom: "10px" }}>{title}</div>
      <div style={{ display: "grid", gap: "8px" }}>
        {options.map((option) => (
          <label key={option.value}>
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={value === option.value}
              onChange={(e) => onChange(e.target.value)}
            />
            {" "}
            {option.label}
          </label>
        ))}
      </div>
    </div>
  );
}

function CheckboxGroup({ title, options, selectedValues, onChange }) {
  const handleToggle = (value) => {
    if (selectedValues.includes(value)) {
      onChange(selectedValues.filter((item) => item !== value));
    } else {
      onChange([...selectedValues, value]);
    }
  };

  return (
    <div style={{ marginBottom: "22px" }}>
      <div style={{ fontWeight: "bold", marginBottom: "10px" }}>{title}</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
        {options.map((option) => (
          <label key={option}>
            <input
              type="checkbox"
              checked={selectedValues.includes(option)}
              onChange={() => handleToggle(option)}
            />
            {" "}
            {getFieldLabel(option)}
          </label>
        ))}
      </div>
    </div>
  );
}

export default function App() {
  const [studyForm, setStudyForm] = useState({
    country: "",
    has_high_school_graduation: "",
    wants_to_continue_same_field: "",
    main_school_focus: "",
    advanced_subjects: [],
    favorite_subjects: [],
    best_subjects: [],
  });

  const [preferencesForm, setPreferencesForm] = useState({
    job_style_preference: "",
    work_environment_preference: "",
    preferred_field: "",
    self_learning_comfort: "",
    long_learning_willingness: "",
    learning_structure_preference: "",
    openness_to_new_fields: "",
  });

  const [responseData, setResponseData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleStudyChange = (field, value) => {
    setStudyForm((prev) => ({ ...prev, [field]: value }));
  };

  const handlePreferencesChange = (field, value) => {
    setPreferencesForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    try {
      setLoading(true);
      setError("");

      const payload = {
        study_form: studyForm,
        preferences_form: preferencesForm,
      };

      const res = await fetch(`${API_BASE_URL}/analyze`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(errorText || "Failed to submit questionnaire.");
      }

      const result = await res.json();
      setResponseData(result);
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: "20px" }}>
      <form onSubmit={handleSubmit}>
        <button type="submit" disabled={loading}>
          {loading ? "Submitting..." : "Submit"}
        </button>

        {error && <div style={{ color: "red" }}>{error}</div>}

        {responseData && (
          <pre>{JSON.stringify(responseData, null, 2)}</pre>
        )}
      </form>
    </div>
  );
}