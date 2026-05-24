import React, { useMemo, useState } from "react";

function DataTable({ rows }) {
  if (!rows.length) return <p>No rows to display.</p>;
  const keys = Object.keys(rows[0]);
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {keys.map((key) => (
              <th key={key}>{key}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr key={idx}>
              {keys.map((key) => (
                <td key={`${idx}-${key}`}>{String(row[key] ?? "")}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SummaryCard({ title, value, tone = "ink" }) {
  return (
    <div className={`summary-card tone-${tone}`}>
      <p className="meta">{title}</p>
      <div className="summary-value">{value ?? "-"}</div>
    </div>
  );
}

function LogList({ title, items, query }) {
  const filtered = (items || []).filter((item) =>
    String(item).toLowerCase().includes(query.toLowerCase())
  );
  const display = query ? filtered : items || [];

  return (
    <div className="log-card">
      <div className="log-title">{title}</div>
      <div className="log-body">
        {display.length ? (
          <ul>
            {display.slice(0, 200).map((item, idx) => (
              <li key={`${title}-${idx}`}>{String(item)}</li>
            ))}
          </ul>
        ) : (
          <p className="meta">Nothing recorded.</p>
        )}
      </div>
    </div>
  );
}

function buildGuideChecklist() {
  return [
    "Upload the Excel export on the Life Skill allocator upload card.",
    "Review detected skills and sections, then adjust slots/capacities if needed.",
    "Set xWeight and section skill limit.",
    "Click Run Allocation.",
    "Open Results and ask questions in AI Assistance.",
    "Use the example prompts below to ask for student lists, counts, or summaries.",
  ];
}

function buildPromptExamples() {
  return [
    "Show the students in ML course section 2 with their previous dept elective.",
    "List all students in Cookery section 1.",
    "How many students are allocated in each section?",
    "Show the unallocated students.",
    "Give me the summary of allocation results.",
    "What are the top skills after allocation?",
  ];
}

function extractSection(question) {
  const match = question.match(/\b(?:section|sec)\s*(\d+)\b/i);
  return match ? match[1] : null;
}

function normalizeText(value) {
  return String(value ?? "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .replace(/\s+/g, " ");
}

function tokenize(value) {
  return normalizeText(value).split(" ").filter(Boolean);
}

function levenshteinDistance(left, right) {
  const a = String(left ?? "");
  const b = String(right ?? "");

  if (!a.length) return b.length;
  if (!b.length) return a.length;

  const previousRow = Array.from({ length: b.length + 1 }, (_, idx) => idx);

  for (let i = 1; i <= a.length; i += 1) {
    let diagonal = i - 1;
    let current = i;

    for (let j = 1; j <= b.length; j += 1) {
      const saved = previousRow[j];
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      current = Math.min(previousRow[j] + 1, current + 1, diagonal + cost);
      previousRow[j] = current;
      diagonal = saved;
    }

    previousRow[0] = i;
  }

  return previousRow[b.length];
}

function scoreCourseMatch(candidate, query) {
  const candidateText = normalizeText(candidate);
  const queryText = normalizeText(query);
  if (!candidateText || !queryText) return 0;

  if (queryText.includes(candidateText) || candidateText.includes(queryText)) {
    return 1;
  }

  const candidateTokens = tokenize(candidateText);
  const queryTokens = tokenize(queryText);
  if (!candidateTokens.length || !queryTokens.length) return 0;

  let matchedTokens = 0;
  for (const candidateToken of candidateTokens) {
    const tokenMatched = queryTokens.some((queryToken) => {
      if (candidateToken === queryToken) return true;
      if (candidateToken.includes(queryToken) || queryToken.includes(candidateToken)) return true;
      return levenshteinDistance(candidateToken, queryToken) <= (candidateToken.length <= 4 ? 1 : 2);
    });
    if (tokenMatched) matchedTokens += 1;
  }

  const tokenScore = matchedTokens / candidateTokens.length;
  const compactCandidate = candidateText.replace(/\s+/g, "");
  const compactQuery = queryText.replace(/\s+/g, "");
  const ratio =
    1 - levenshteinDistance(compactCandidate, compactQuery) / Math.max(compactCandidate.length, compactQuery.length, 1);

  return Math.max(tokenScore, ratio * 0.8);
}

function matchesCourse(skill, course) {
  return scoreCourseMatch(skill, course) >= 0.55;
}

function extractCourse(question, knownCourses) {
  const lowered = normalizeText(question);

  for (const course of knownCourses) {
    const c = String(course || "").trim();
    if (!c) continue;
    if (lowered.includes(normalizeText(c))) return c;
  }

  if (lowered.includes("machine learning") || lowered.includes(" ml ")) {
    return "ML";
  }

  let bestCourse = null;
  let bestScore = 0;

  for (const course of knownCourses) {
    const score = scoreCourseMatch(course, question);
    if (score > bestScore) {
      bestCourse = course;
      bestScore = score;
    }
  }

  if (bestScore >= 0.55) return bestCourse;

  const generic = question.match(/\bcourse\s+([a-z0-9\- ]+)/i);
  return generic ? generic[1].trim() : null;
}

function Results({
  result,
  searchTerm,
  onSearchChange,
  logSearch = "",
  onLogSearchChange = () => {},
  activeTab,
  onTabChange,
  filteredStudents,
  capacityBySlot,
  topSkills,
  unallocatedRows,
  downloadSheet,
  downloadLogs,
  downloadAll,
  onBack,
}) {
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [assistantQuestion, setAssistantQuestion] = useState(
    "Give me the list of students in ML course section 2 with previous dept elective"
  );
  const [assistantAnswer, setAssistantAnswer] = useState(null);
  const promptExamples = useMemo(() => buildPromptExamples(), []);

  const knownCourses = useMemo(() => {
    return (result?.skillWise || [])
      .map((row) => String(row?.Skill || "").trim())
      .filter(Boolean)
      .filter((value, idx, arr) => arr.indexOf(value) === idx);
  }, [result]);

  const runAssistant = () => {
    const rows = result?.studentWise || [];
    if (!rows.length) {
      setAssistantAnswer({
        kind: "text",
        title: "Allocation not available",
        message: "Please run the allocation first.",
        guidelines: buildGuideChecklist(),
      });
      return;
    }

    const q = (assistantQuestion || "").trim();
    const lower = q.toLowerCase();

    if (!q) {
      setAssistantAnswer({
        kind: "text",
        title: "Ask a question",
        message: "Type a question to get student lists, summary, or guidelines.",
      });
      return;
    }

    if (
      lower.includes("guide") ||
      lower.includes("guideline") ||
      lower.includes("how to run") ||
      lower.includes("steps")
    ) {
      setAssistantAnswer({
        kind: "text",
        title: "Allocation checklist",
        message: "Follow these steps:",
        guidelines: buildGuideChecklist(),
      });
      return;
    }

    if (lower.includes("summary") || lower.includes("how many") || lower.includes("total")) {
      setAssistantAnswer({
        kind: "summary",
        title: "Allocation summary",
        summary: {
          studentsLoaded: result.summary?.studentsLoaded ?? 0,
          studentsAllocated: result.summary?.studentsAllocated ?? 0,
          duplicateStudentsRemoved: result.summary?.duplicateStudentsRemoved ?? 0,
          invalidCgpaRowsRemoved: result.summary?.invalidCgpaRowsRemoved ?? 0,
        },
      });
      return;
    }

    if (lower.includes("top skill") || lower.includes("top skills") || lower.includes("most skill")) {
      setAssistantAnswer({
        kind: "table",
        title: "Top skills",
        message: "Showing the current skill allocation summary.",
        rows: (topSkills || []).slice(0, 200).map(({ skill, count }) => ({ Skill: skill, Count: count })),
      });
      return;
    }

    if (lower.includes("section wise") || lower.includes("section-wise") || lower.includes("by section")) {
      setAssistantAnswer({
        kind: "table",
        title: "Section-wise results",
        message: "Showing section-wise allocation rows from the current results.",
        rows: (result.sectionWise || []).slice(0, 200),
      });
      return;
    }

    if (lower.includes("skill wise") || lower.includes("skill-wise") || lower.includes("by skill")) {
      setAssistantAnswer({
        kind: "table",
        title: "Skill-wise results",
        message: "Showing skill-wise allocation rows from the current results.",
        rows: (result.skillWise || []).slice(0, 200),
      });
      return;
    }

    if (lower.includes("slot wise") || lower.includes("slot-wise") || lower.includes("by slot")) {
      setAssistantAnswer({
        kind: "table",
        title: "Slot-wise results",
        message: "Showing slot-wise allocation rows from the current results.",
        rows: (result.slotWise || []).slice(0, 200),
      });
      return;
    }

    if (lower.includes("unallocated") || lower.includes("not allocated")) {
      setAssistantAnswer({
        kind: "table",
        title: "Unallocated students",
        message: `Showing up to 200 rows from unallocated output (${unallocatedRows.length} total).`,
        rows: (unallocatedRows || []).slice(0, 200),
      });
      return;
    }

    const section = extractSection(q);
    const course = extractCourse(q, knownCourses);
    const wantsPrevious =
      lower.includes("previous") || lower.includes("completed") || lower.includes("dept elective");

    let filtered = rows;
    if (section) {
      filtered = filtered.filter(
        (row) => String(row?.Section ?? "").trim().toLowerCase() === String(section).toLowerCase()
      );
    }
    if (course) {
      filtered = filtered.filter((row) => matchesCourse(row?.Skill, course));
    }

    if (!filtered.length) {
      setAssistantAnswer({
        kind: "text",
        title: "No match found",
        message: "No students matched this course/section filter in current allocation results.",
      });
      return;
    }

    const responseRows = filtered.slice(0, 200).map((row) => {
      const mapped = {
        RegNo: row?.RegNo ?? "",
        Name: row?.Name ?? "",
        Section: row?.Section ?? "",
        Skill: row?.Skill ?? "",
        Slot: row?.Slot ?? "",
      };
      if (wantsPrevious) {
        mapped.PreviousDeptElective = "Not available in current Life Skill result schema";
      }
      return mapped;
    });

    setAssistantAnswer({
      kind: "table",
      title: "Filtered students",
      message: `Matched ${filtered.length} students. Showing up to 200 rows.`,
      rows: responseRows,
    });
  };

  return (
    <section className="panel results-panel">
      <button
        type="button"
        className={`assistant-fab ${assistantOpen ? "open" : ""}`}
        onClick={() => setAssistantOpen((prev) => !prev)}
        aria-label={assistantOpen ? "Close AI assistance" : "Open AI assistance"}
        aria-pressed={assistantOpen}
        title="AI Assistance"
      >
        AI
      </button>

      <div className="row-actions" style={{ justifyContent: "space-between", marginBottom: 6 }}>
        <div className="meta">Results view</div>
        {onBack && <button className="ghost" onClick={onBack}>Back to settings</button>}
      </div>

      {assistantOpen && (
        <div className="assistant-panel">
          <div className="assistant-header">
            <h3>AI Assistance</h3>
            <span className="meta">Uses current allocation results automatically</span>
          </div>
          <div className="assistant-query">
            <input
              className="search"
              placeholder="Ask about section/course/student summary..."
              value={assistantQuestion}
              onChange={(e) => setAssistantQuestion(e.target.value)}
            />
            <button onClick={runAssistant}>Ask AI</button>
          </div>

          <div className="assistant-examples">
            <div className="assistant-examples-title">Example prompts</div>
            <div className="prompt-chip-list">
              {promptExamples.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  className="prompt-chip"
                  onClick={() => setAssistantQuestion(prompt)}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>

          {assistantAnswer?.kind === "text" && (
            <div className="assistant-answer">
              <h4>{assistantAnswer.title}</h4>
              <p>{assistantAnswer.message}</p>
              {!!assistantAnswer.guidelines?.length && (
                <ol>
                  {assistantAnswer.guidelines.map((item, idx) => (
                    <li key={`g-${idx}`}>{item}</li>
                  ))}
                </ol>
              )}
            </div>
          )}

          {assistantAnswer?.kind === "summary" && (
            <div className="assistant-answer">
              <h4>{assistantAnswer.title}</h4>
              <div className="assistant-summary-grid">
                {Object.entries(assistantAnswer.summary || {}).map(([key, value]) => (
                  <div className="summary-card" key={key}>
                    <p className="meta">{key}</p>
                    <div className="summary-value">{value}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {assistantAnswer?.kind === "table" && (
            <div className="assistant-answer">
              <h4>{assistantAnswer.title}</h4>
              <p className="meta">{assistantAnswer.message}</p>
              <DataTable rows={assistantAnswer.rows || []} />
            </div>
          )}
        </div>
      )}

      <div className="tab-bar">
        {[
          { id: "summary", label: "Summary" },
          { id: "students", label: "Students" },
          { id: "sections", label: "Section-wise" },
          { id: "skills", label: "Skill-wise" },
          { id: "slots", label: "Slot-wise" },
          { id: "capacity", label: "Capacity" },
          { id: "guide", label: "Guide" },
          { id: "logs", label: "Logs" },
        ].map((tab) => (
          <button
            key={tab.id}
            className={`tab-btn ${activeTab === tab.id ? "active" : ""}`}
            onClick={() => onTabChange(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "summary" && (
        <div className="tab-content">
          <div className="summary-grid">
            <SummaryCard title="Students Loaded" value={result.summary?.studentsLoaded} tone="ink" />
            <SummaryCard title="Students Allocated" value={result.summary?.studentsAllocated} tone="success" />
            <SummaryCard title="Duplicate Removed" value={result.summary?.duplicateStudentsRemoved} tone="warn" />
            <SummaryCard title="Invalid CGPA Removed" value={result.summary?.invalidCgpaRowsRemoved} tone="danger" />
          </div>

          <div className="export-row">
            <button onClick={() => downloadSheet(result.studentWise, "student-wise")}>Download Student-wise</button>
            <button onClick={() => downloadSheet(result.sectionWise, "section-wise")}>Download Section-wise</button>
            <button onClick={() => downloadSheet(result.skillWise, "skill-wise")}>Download Skill-wise</button>
            <button onClick={() => downloadSheet(result.capacityDashboard, "capacity-dashboard")}>Download Capacity</button>
            <button onClick={() => downloadSheet(unallocatedRows, "unallocated-overall")}>
              Download Unallocated
            </button>
            <button onClick={downloadLogs}>Download Logs</button>
            <button onClick={downloadAll}>Download Workbook</button>
          </div>

          <div className="panel inset">
            <div className="panel-heading">
              <h3>Top Skills</h3>
              <span className="meta">by allocations</span>
            </div>
            <div className="chip-list">
              {topSkills.map(({ skill, count }) => (
                <div key={skill} className="chip">
                  <span>{skill}</span>
                  <span className="pill">{count}</span>
                </div>
              ))}
              {!topSkills.length && <p className="meta">No skill data.</p>}
            </div>
          </div>
        </div>
      )}

      {activeTab === "students" && (
        <div className="tab-content">
          <div className="panel inset">
            <div className="panel-heading stack">
              <div>
                <h3>Find a Student</h3>
                <p className="meta">Search by reg no, name, section, slot, or skill. Showing up to 200 hits.</p>
              </div>
              <input
                className="search"
                placeholder="Search students..."
                value={searchTerm}
                onChange={(e) => onSearchChange(e.target.value)}
              />
            </div>
            <DataTable rows={filteredStudents} />
          </div>
        </div>
      )}

      {activeTab === "sections" && (
        <div className="tab-content">
          <div className="panel inset">
            <div className="panel-heading">
              <h3>Section-wise</h3>
            </div>
            <DataTable rows={result.sectionWise || []} />
          </div>
        </div>
      )}

      {activeTab === "skills" && (
        <div className="tab-content">
          <div className="panel inset">
            <div className="panel-heading">
              <h3>Skill-wise</h3>
            </div>
            <DataTable rows={result.skillWise || []} />
          </div>
        </div>
      )}

      {activeTab === "slots" && (
        <div className="tab-content">
          <div className="panel inset">
            <div className="panel-heading">
              <h3>Slot-wise</h3>
            </div>
            <DataTable rows={result.slotWise || []} />
          </div>
        </div>
      )}

      {activeTab === "capacity" && (
        <div className="tab-content">
          <div className="panel inset">
            <div className="panel-heading">
              <h3>Slot Capacity Usage</h3>
              <span className="meta">live after allocation</span>
            </div>
            <div className="slot-grid">
              {capacityBySlot.map(({ slot, items }) => (
                <div key={slot} className="slot-card">
                  <div className="slot-title">{slot}</div>
                  {items.map(({ Skill, Allocated, Capacity }) => {
                    const pct = Math.min(100, Math.round((Allocated / Capacity) * 100));
                    return (
                      <div key={`${slot}-${Skill}`} className="bar-row">
                        <div className="bar-label">
                          <span>{Skill}</span>
                          <span className="meta">{Allocated}/{Capacity}</span>
                        </div>
                        <div className="bar-shell">
                          <div className="bar-fill" style={{ width: `${pct}%` }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              ))}
              {!capacityBySlot.length && <p className="meta">No capacity data.</p>}
            </div>
          </div>
          <div className="panel inset">
            <div className="panel-heading">
              <h3>Capacity Table</h3>
            </div>
            <DataTable rows={result.capacityDashboard || []} />
          </div>
        </div>
      )}

      {activeTab === "logs" && (
        <div className="tab-content">
          <div className="panel inset">
            <div className="panel-heading stack">
              <h3>Allocation Logs</h3>
              <div className="meta">Use download for full text</div>
              <input
                className="search"
                placeholder="Search logs..."
                value={logSearch}
                onChange={(e) => onLogSearchChange(e.target.value)}
              />
            </div>
            <div className="log-grid">
              <LogList title="Allocation" items={result.logs?.allocationLog || []} query={logSearch} />
              <LogList title="Duplicate Students Removed" items={result.logs?.duplicateStudentsRemoved || []} query={logSearch} />
              <LogList title="Invalid CGPA Rows" items={result.logs?.invalidCgpaRows || []} query={logSearch} />
            </div>
          </div>
        </div>
      )}

      {activeTab === "guide" && (
        <div className="tab-content">
          <div className="panel inset">
            <div className="panel-heading stack">
              <h3>Google Form Setup (Life Skill)</h3>
              <p className="meta">Keep column headers identical so the allocator auto-detects them.</p>
            </div>
            <ul>
              <li>Required columns: Student Name, Register Number, CGPA, Section.</li>
              <li>Preference columns: Row1, Row2, Row3... (any header containing "row", "pref", "choice", or "skill" works).</li>
              <li>Optional: Attendance column (0-10 scale) to blend with CGPA via xWeight.</li>
              <li>Form responses export: open Google Form responses sheet → File → Download → Microsoft Excel (.xlsx) before upload.</li>
            </ul>
          </div>

          <div className="panel inset">
            <div className="panel-heading stack">
              <h3>Run the Allocation</h3>
              <p className="meta">Steps faculty can follow inside the Life Skill allocator.</p>
            </div>
            <ol>
              <li>Upload the Excel export (from the Google Form) on the Life Skill allocator upload card.</li>
              <li>Review auto-detected skills and sections; adjust slot count, section-slot mapping, and skill capacities if needed.</li>
              <li>Set attendance weight (xWeight) and section skill limit, then click Run Allocation.</li>
              <li>Use the tabs to review results; download Student/Section/Skill/Slot wise sheets, Capacity, Unallocated, and Logs.</li>
              <li>If data changes, re-upload the updated Excel and re-run.</li>
            </ol>
          </div>
        </div>
      )}
    </section>
  );
}

export default Results;
