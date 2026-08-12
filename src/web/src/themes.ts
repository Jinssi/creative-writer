// Themes drive both the look and the writing effort. Selecting a theme changes
// the example prompts and injects domain guidance into the writing request, so the
// same agents produce content tuned to the chosen creative domain.

export interface ThemeExample {
  research: string;
  references: string;
  assignment: string;
}

export interface Theme {
  id: string;
  name: string;
  emoji: string;
  tagline: string;
  accent: string; // hex, used for the theme chip / accents
  domain: string; // guidance prepended to the writing assignment
  labels: { research: string; references: string; assignment: string };
  examples: ThemeExample[];
}

export const THEMES: Theme[] = [
  {
    id: "outdoor",
    name: "Outdoor Adventure",
    emoji: "🏔️",
    tagline: "Trails, gear and the great outdoors",
    accent: "#7c3aed",
    domain:
      "You are writing for an outdoor adventure magazine. Use an energetic, trail-savvy voice that inspires readers to get outside.",
    labels: { research: "Research", references: "Gear & references", assignment: "Assignment" },
    examples: [
      {
        research: "Find the latest winter camping trends and what people are doing in the cold season.",
        references: "Reference a selection of 4-season tents and cold-weather sleeping bags.",
        assignment:
          "Write a fun, engaging 800-1000 word article that weaves in the research and gear. Cite sources inline as you mention them.",
      },
      {
        research: "Research ultralight backpacking essentials and how to cut pack weight.",
        references: "Reference ultralight trekking-pole tents and insulated sleeping pads.",
        assignment: "Write an ~800 word article on ultralight backpacking with inline citations.",
      },
    ],
  },
  {
    id: "tech",
    name: "Technology & Gadgets",
    emoji: "💻",
    tagline: "Reviews, how-tos and what's next",
    accent: "#2563eb",
    domain:
      "You are writing for a technology publication. Use a clear, curious, and precise voice that makes complex topics approachable.",
    labels: { research: "Research", references: "Products & sources", assignment: "Assignment" },
    examples: [
      {
        research: "Find the biggest trends in on-device AI and what it means for everyday users.",
        references: "Reference a selection of recent AI-capable laptops and phones.",
        assignment: "Write a ~900 word explainer with inline citations and a practical buyer's takeaway.",
      },
      {
        research: "Research the shift to passwordless authentication and passkeys.",
        references: "Reference popular password managers and passkey-enabled services.",
        assignment: "Write an ~800 word article explaining passkeys for a general audience, citing sources inline.",
      },
    ],
  },
  {
    id: "travel",
    name: "Travel & Places",
    emoji: "🧭",
    tagline: "Destinations, guides and journeys",
    accent: "#0891b2",
    domain:
      "You are writing for a travel publication. Use an evocative, sensory voice that transports the reader while staying practical.",
    labels: { research: "Research", references: "Places & sources", assignment: "Assignment" },
    examples: [
      {
        research: "Find under-the-radar autumn city breaks in Europe and why they shine off-season.",
        references: "Reference a few walkable neighborhoods and local food spots.",
        assignment: "Write a ~900 word travel guide with inline citations and a suggested 2-day itinerary.",
      },
      {
        research: "Research tips for slow travel by train across Scandinavia.",
        references: "Reference scenic rail routes and comfortable overnight options.",
        assignment: "Write an ~800 word article on slow train travel, citing sources inline.",
      },
    ],
  },
  {
    id: "food",
    name: "Food & Cooking",
    emoji: "🍳",
    tagline: "Recipes, techniques and flavor",
    accent: "#ea580c",
    domain:
      "You are writing for a food and cooking publication. Use a warm, appetizing voice with clear, confidence-building guidance.",
    labels: { research: "Research", references: "Ingredients & sources", assignment: "Assignment" },
    examples: [
      {
        research: "Find approachable techniques for weeknight sheet-pan dinners.",
        references: "Reference versatile pantry staples and seasonal vegetables.",
        assignment: "Write a ~800 word article with 2-3 example flavor combinations, citing sources inline.",
      },
    ],
  },
  {
    id: "wellness",
    name: "Health & Wellness",
    emoji: "🌿",
    tagline: "Movement, mindfulness and balance",
    accent: "#16a34a",
    domain:
      "You are writing for a health and wellness publication. Use a supportive, evidence-aware voice. Avoid medical claims; cite reputable sources.",
    labels: { research: "Research", references: "Practices & sources", assignment: "Assignment" },
    examples: [
      {
        research: "Find realistic habits for better sleep backed by recent research.",
        references: "Reference simple evening routines and wind-down practices.",
        assignment: "Write a ~800 word, encouraging article with inline citations to reputable sources.",
      },
    ],
  },
  {
    id: "business",
    name: "Business & Ideas",
    emoji: "📈",
    tagline: "Strategy, work and growth",
    accent: "#4f46e5",
    domain:
      "You are writing for a business and ideas publication. Use a crisp, insightful voice with concrete takeaways for professionals.",
    labels: { research: "Research", references: "Examples & sources", assignment: "Assignment" },
    examples: [
      {
        research: "Find what makes async-first teams effective and where they struggle.",
        references: "Reference common collaboration tools and team rituals.",
        assignment: "Write a ~900 word article with inline citations and a short checklist.",
      },
    ],
  },
];

export const DEFAULT_THEME_ID = "outdoor";

export const getTheme = (id: string): Theme =>
  THEMES.find((t) => t.id === id) ?? THEMES[0];
