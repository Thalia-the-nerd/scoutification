// Configuration for FRC Scouting Form
// This defines all the fields that will be displayed in the scouting interface

const CONFIG = {
  fields: [
    // Basic Match Information
    {
      id: "team_number",
      label: "Team Number",
      type: "number",
      required: true,
      category: "match_info"
    },
    {
      id: "scouter_name",
      label: "Scouter Name",
      type: "text",
      required: true,
      category: "match_info"
    },

    // Autonomous Period
    {
      id: "auto_balls_scored_upper",
      label: "Auto: Balls Scored (Upper Hub)",
      type: "counter",
      min: 0,
      max: 50,
      category: "autonomous"
    },
    {
      id: "auto_balls_scored_lower",
      label: "Auto: Balls Scored (Lower Hub)",
      type: "counter",
      min: 0,
      max: 50,
      category: "autonomous"
    },
    {
      id: "auto_taxi",
      label: "Auto: Left Tarmac (Taxi)",
      type: "checkbox",
      category: "autonomous"
    },

    // Teleop Period
    {
      id: "teleop_balls_scored_upper",
      label: "Teleop: Balls Scored (Upper Hub)",
      type: "counter",
      min: 0,
      max: 100,
      category: "teleop"
    },
    {
      id: "teleop_balls_scored_lower",
      label: "Teleop: Balls Scored (Lower Hub)",
      type: "counter",
      min: 0,
      max: 100,
      category: "teleop"
    },
    {
      id: "teleop_balls_missed",
      label: "Teleop: Balls Missed",
      type: "counter",
      min: 0,
      max: 100,
      category: "teleop"
    },

    // Endgame
    {
      id: "climb_level",
      label: "Climb Level",
      type: "dropdown",
      options: ["None", "Low", "Mid", "High", "Traversal"],
      category: "endgame"
    },
    {
      id: "climb_time",
      label: "Climb Time (seconds)",
      type: "number",
      min: 0,
      max: 135,
      category: "endgame"
    },

    // Defense and Notes
    {
      id: "defense_rating",
      label: "Defense Rating",
      type: "dropdown",
      options: ["None", "Poor", "Average", "Good", "Excellent"],
      category: "performance"
    },
    {
      id: "driver_skill",
      label: "Driver Skill",
      type: "dropdown",
      options: ["Poor", "Average", "Good", "Excellent"],
      category: "performance"
    },
    {
      id: "penalties",
      label: "Penalties/Fouls",
      type: "counter",
      min: 0,
      max: 20,
      category: "performance"
    },
    {
      id: "broke_down",
      label: "Robot Broke Down",
      type: "checkbox",
      category: "performance"
    },
    {
      id: "notes",
      label: "Additional Notes",
      type: "textarea",
      category: "notes"
    }
  ],

  // Category display names for grouping
  categories: {
    match_info: "Match Information",
    autonomous: "Autonomous Period",
    teleop: "Teleoperated Period",
    endgame: "Endgame",
    performance: "Performance Assessment",
    notes: "Notes"
  }
};

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CONFIG;
}
