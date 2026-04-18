import { useState } from "react";

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
    <div
      style={{
        background: "#ffffff",
        border: "1px solid #e5e7eb",
        borderRadius: "16px",
        padding: "20px",
        boxShadow: "0 4px 20px rgba(0,0,0,0.04)",
        height: "100%",
        overflow: "auto",
        boxSizing: "border-box",
      }}
    >
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
          <label key={option.value} style={{ lineHeight: 1.4 }}>
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
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
          gap: "8px 14px",
        }}
      >
        {options.map((option) => (
          <label key={option} style={{ lineHeight: 1.4 }}>
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

function RecommendationCard({ item, index }) {
  return (
    <div
      style={{
        border: "1px solid #dbeafe",
        background: "#eff6ff",
        borderRadius: "14px",
        padding: "16px",
      }}
    >
      <div style={{ marginBottom: "8px", fontSize: "14px", color: "#1d4ed8" }}>
        Recommendation #{index + 1}
      </div>
      <h3 style={{ margin: "0 0 10px 0", textTransform: "capitalize" }}>
        {getFieldLabel(item.field)}
      </h3>
      <div style={{ marginBottom: "8px", color: "#334155" }}>
        <strong>Label:</strong> {item.label}
      </div>
      <div style={{ marginBottom: "10px", color: "#334155" }}>
        <strong>Confidence:</strong> {item.confidence}
      </div>
      <div style={{ color: "#0f172a", lineHeight: 1.5 }}>{item.reason}</div>
    </div>
  );
}

function DebugFieldCard({ item }) {
  return (
    <div
      style={{
        border: "1px solid #e5e7eb",
        borderRadius: "12px",
        padding: "14px",
        background: "#ffffff",
      }}
    >
      <div style={{ marginBottom: "8px" }}>
        <strong>{getFieldLabel(item.field)}</strong>
      </div>
      <div style={{ fontSize: "14px", color: "#334155", display: "grid", gap: "4px" }}>
        <div><strong>Final label:</strong> {item.final_label}</div>
        <div><strong>Final score:</strong> {item.final_score}</div>
        <div><strong>Confidence:</strong> {item.confidence}</div>
        <div><strong>Past signal:</strong> {item.past_signal}</div>
        <div><strong>Preferences signal:</strong> {item.preferences_signal}</div>
        <div><strong>Market signal:</strong> {item.market_signal}</div>
        <div><strong>Conflict type:</strong> {item.conflict_type}</div>
      </div>

      {item.dominant_reason && (
        <div style={{ marginTop: "10px", lineHeight: 1.5 }}>
          <strong>Reason:</strong> {item.dominant_reason}
        </div>
      )}

      {item.market_career_outcomes?.length > 0 && (
        <div style={{ marginTop: "10px", lineHeight: 1.5 }}>
          <strong>Possible outcomes:</strong> {item.market_career_outcomes.join(", ")}
        </div>
      )}
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

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResponseData(null);

    try {
      const payload = {
        study: studyForm,
        preferences: preferencesForm,
      };

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

  const handleSubmit = async () => {
    try {
      setLoading(true);
      setError("");

      const payload = data;

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

  const finalResult = responseData?.result?.final_result || null;
  const userResult = finalResult?.user_result || null;
  const debugResult = finalResult?.debug_result || null;

  const topRecommendations = userResult?.top_3_recommendations || [];
  const summary = userResult?.summary || "";
  const warning = userResult?.warning || "";

  return (
    <div
      style={{
        height: "100vh",
        background: "#f8fafc",
        padding: "16px",
        boxSizing: "border-box",
        fontFamily: "Arial, sans-serif",
      }}
    >
      <form
        onSubmit={handleSubmit}
        style={{
          height: "100%",
          display: "grid",
          gridTemplateRows: "1fr 1fr",
          gap: "16px",
        }}
      >
        {/* TOP HALF */}
        <div
          style={{
            minHeight: 0,
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "16px",
          }}
        >
          {/* TOP LEFT */}
          <SectionCard title="Study Background">
            <div style={{ marginBottom: "22px" }}>
              <div style={{ fontWeight: "bold", marginBottom: "10px" }}>
                1. Which country are you from?
              </div>
              <input
                type="text"
                value={studyForm.country}
                onChange={(e) => handleStudyChange("country", e.target.value)}
                style={{
                  width: "100%",
                  padding: "10px",
                  border: "1px solid #cbd5e1",
                  borderRadius: "10px",
                  boxSizing: "border-box",
                }}
              />
            </div>

            <RadioGroup
              title="2. Do you have a high school graduation certificate?"
              name="has_high_school_graduation"
              value={studyForm.has_high_school_graduation}
              onChange={(value) =>
                handleStudyChange("has_high_school_graduation", value)
              }
              options={[
                { label: "Yes", value: "yes" },
                { label: "No", value: "no" },
                { label: "Prefer not to say", value: "prefer_not_to_answer" },
              ]}
            />

            <RadioGroup
              title="3. Would you like to continue in the same field you studied at school?"
              name="wants_to_continue_same_field"
              value={studyForm.wants_to_continue_same_field}
              onChange={(value) =>
                handleStudyChange("wants_to_continue_same_field", value)
              }
              options={[
                { label: "Yes", value: "yes" },
                { label: "No", value: "no" },
                { label: "Not sure", value: "unsure" },
              ]}
            />

            <RadioGroup
              title="4. What was your main school focus?"
              name="main_school_focus"
              value={studyForm.main_school_focus}
              onChange={(value) =>
                handleStudyChange("main_school_focus", value)
              }
              options={[
                { label: "Humanities", value: "humanities" },
                { label: "Science", value: "science" },
                { label: "Arts", value: "arts" },
                { label: "Other / Prefer not to say", value: "other" },
              ]}
            />

            <CheckboxGroup
              title="5. Which subjects did you study at an advanced level?"
              options={SUBJECT_OPTIONS}
              selectedValues={studyForm.advanced_subjects}
              onChange={(value) =>
                handleStudyChange("advanced_subjects", value)
              }
            />

            <CheckboxGroup
              title="6. Which subjects did you enjoy the most?"
              options={SUBJECT_OPTIONS}
              selectedValues={studyForm.favorite_subjects}
              onChange={(value) =>
                handleStudyChange("favorite_subjects", value)
              }
            />

            <CheckboxGroup
              title="7. Which subjects were you best at (highest grades)?"
              options={SUBJECT_OPTIONS}
              selectedValues={studyForm.best_subjects}
              onChange={(value) => handleStudyChange("best_subjects", value)}
            />
          </SectionCard>

          {/* TOP RIGHT */}
          <SectionCard title="Preferences and Work Style">
            <RadioGroup
              title="1. Do you prefer jobs that involve thinking or hands-on work?"
              name="job_style_preference"
              value={preferencesForm.job_style_preference}
              onChange={(value) =>
                handlePreferencesChange("job_style_preference", value)
              }
              options={[
                { label: "Thinking", value: "thinking" },
                { label: "Hands-on work", value: "hands_on" },
                { label: "Not sure", value: "unclear" },
              ]}
            />

            <RadioGroup
              title="2. Do you prefer working in a team or alone?"
              name="work_environment_preference"
              value={preferencesForm.work_environment_preference}
              onChange={(value) =>
                handlePreferencesChange("work_environment_preference", value)
              }
              options={[
                { label: "Team", value: "team" },
                { label: "Alone", value: "alone" },
                { label: "Both / Mixed", value: "mixed" },
                { label: "Not sure", value: "unclear" },
              ]}
            />

            <RadioGroup
              title="3. Which field would you like to work in?"
              name="preferred_field"
              value={preferencesForm.preferred_field}
              onChange={(value) =>
                handlePreferencesChange("preferred_field", value)
              }
              options={[
                { label: "Humanities", value: "humanities" },
                { label: "Science", value: "science" },
                { label: "Hands-on work", value: "hands_on_work" },
                { label: "Arts", value: "arts" },
                { label: "Not sure", value: "unclear" },
              ]}
            />

            <RadioGroup
              title="4. Are you comfortable with self-learning?"
              name="self_learning_comfort"
              value={preferencesForm.self_learning_comfort}
              onChange={(value) =>
                handlePreferencesChange("self_learning_comfort", value)
              }
              options={[
                { label: "Yes", value: "yes" },
                { label: "No", value: "no" },
                { label: "Not sure", value: "unclear" },
              ]}
            />

            <RadioGroup
              title="5. Are you willing to invest a long time in learning?"
              name="long_learning_willingness"
              value={preferencesForm.long_learning_willingness}
              onChange={(value) =>
                handlePreferencesChange("long_learning_willingness", value)
              }
              options={[
                { label: "Yes", value: "yes" },
                { label: "No", value: "no" },
                { label: "Not sure", value: "unclear" },
              ]}
            />

            <RadioGroup
              title="6. Do you prefer structured learning or flexible (self-paced) learning?"
              name="learning_structure_preference"
              value={preferencesForm.learning_structure_preference}
              onChange={(value) =>
                handlePreferencesChange("learning_structure_preference", value)
              }
              options={[
                { label: "Structured", value: "structured" },
                { label: "Flexible / Self-paced", value: "flexible" },
                { label: "Both / Mixed", value: "mixed" },
                { label: "Not sure", value: "unclear" },
              ]}
            />

            <RadioGroup
              title="7. Are you open to trying new areas of study?"
              name="openness_to_new_fields"
              value={preferencesForm.openness_to_new_fields}
              onChange={(value) =>
                handlePreferencesChange("openness_to_new_fields", value)
              }
              options={[
                { label: "Yes", value: "yes" },
                { label: "No", value: "no" },
                { label: "Not sure", value: "unclear" },
              ]}
            />
          </SectionCard>
        </div>

        {/* BOTTOM HALF */}
        <div
          style={{
            minHeight: 0,
            background: "#ffffff",
            border: "1px solid #e5e7eb",
            borderRadius: "16px",
            padding: "20px",
            boxShadow: "0 4px 20px rgba(0,0,0,0.04)",
            overflow: "auto",
            boxSizing: "border-box",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "16px",
              gap: "16px",
              flexWrap: "wrap",
            }}
          >
            <div>
              <h2 style={{ margin: 0, marginBottom: "6px" }}>Results Area</h2>
              <p style={{ margin: 0, color: "#475569" }}>
                Main recommendation appears first, detailed logs below it.
              </p>
            </div>

            <button
              type="submit"
              disabled={loading}
              style={{
                padding: "12px 20px",
                fontSize: "16px",
                borderRadius: "10px",
                border: "none",
                background: "#2563eb",
                color: "white",
                cursor: "pointer",
              }}
            >
              {loading ? "Submitting..." : "Submit"}
            </button>
          </div>

          {error && (
            <div style={{ color: "red", marginBottom: "16px" }}>
              <strong>Error:</strong> {error}
            </div>
          )}

          {!responseData && !loading && (
            <div
              style={{
                height: "calc(100% - 70px)",
                minHeight: "180px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#64748b",
                border: "1px dashed #cbd5e1",
                borderRadius: "12px",
              }}
            >
              The final recommendations will appear here after submission.
            </div>
          )}

          {loading && (
            <div
              style={{
                minHeight: "180px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#475569",
              }}
            >
              Generating recommendations...
            </div>
          )}

          {responseData && finalResult && (
            <div style={{ display: "grid", gap: "18px" }}>
              {/* MAIN RESULT FIRST */}
              <div>
                <h3 style={{ marginTop: 0, marginBottom: "12px" }}>
                  Top Recommendations
                </h3>

                {topRecommendations.length > 0 ? (
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
                      gap: "14px",
                    }}
                  >
                    {topRecommendations.map((item, index) => (
                      <RecommendationCard
                        key={`${item.field}-${index}`}
                        item={item}
                        index={index}
                      />
                    ))}
                  </div>
                ) : (
                  <div
                    style={{
                      padding: "16px",
                      borderRadius: "12px",
                      background: "#f8fafc",
                      color: "#475569",
                    }}
                  >
                    No top recommendations were returned.
                  </div>
                )}
              </div>

              {summary && (
                <div
                  style={{
                    background: "#f8fafc",
                    border: "1px solid #e5e7eb",
                    borderRadius: "12px",
                    padding: "16px",
                  }}
                >
                  <strong>Summary</strong>
                  <div style={{ marginTop: "8px", lineHeight: 1.5 }}>{summary}</div>
                </div>
              )}

              {warning && (
                <div
                  style={{
                    background: "#fff7ed",
                    border: "1px solid #fdba74",
                    borderRadius: "12px",
                    padding: "16px",
                  }}
                >
                  <strong>Warning</strong>
                  <div style={{ marginTop: "8px", lineHeight: 1.5 }}>{warning}</div>
                </div>
              )}

              {/* DEBUG DETAILS */}
              <details
                style={{
                  border: "1px solid #e5e7eb",
                  borderRadius: "12px",
                  padding: "14px 16px",
                  background: "#fafafa",
                }}
              >
                <summary style={{ cursor: "pointer", fontWeight: "bold" }}>
                  Debug Details
                </summary>

                <div style={{ marginTop: "16px", display: "grid", gap: "16px" }}>
                  {debugResult?.top_conflicts?.length > 0 && (
                    <div>
                      <h4 style={{ marginTop: 0, marginBottom: "10px" }}>
                        Top Conflicts
                      </h4>
                      <div style={{ display: "grid", gap: "10px" }}>
                        {debugResult.top_conflicts.map((item, index) => (
                          <div
                            key={`${item.field}-${index}`}
                            style={{
                              background: "#ffffff",
                              border: "1px solid #e5e7eb",
                              borderRadius: "10px",
                              padding: "12px",
                            }}
                          >
                            <div>
                              <strong>{getFieldLabel(item.field)}</strong> — {item.conflict_type}
                            </div>
                            <div style={{ marginTop: "6px", lineHeight: 1.5 }}>
                              {item.explanation}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {debugResult?.all_fields?.length > 0 && (
                    <div>
                      <h4 style={{ marginTop: 0, marginBottom: "10px" }}>
                        All Fields Analysis
                      </h4>
                      <div style={{ display: "grid", gap: "12px" }}>
                        {debugResult.all_fields.map((item, index) => (
                          <DebugFieldCard
                            key={`${item.field}-${index}`}
                            item={item}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </details>

              {/* RAW JSON */}
              <details
                style={{
                  border: "1px solid #e5e7eb",
                  borderRadius: "12px",
                  padding: "14px 16px",
                  background: "#fafafa",
                }}
              >
                <summary style={{ cursor: "pointer", fontWeight: "bold" }}>
                  Raw JSON
                </summary>
                <pre
                  style={{
                    marginTop: "16px",
                    background: "#f8fafc",
                    padding: "16px",
                    borderRadius: "10px",
                    overflowX: "auto",
                  }}
                >
                  {JSON.stringify(responseData, null, 2)}
                </pre>
              </details>
            </div>
          )}
        </div>
      </form>
    </div>
  );
}