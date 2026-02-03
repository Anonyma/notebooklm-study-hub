-- NotebookLM Study Hub: Enhanced Schema
-- Migration: Create tables for rich articles, entities, images, and timeline

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- TIMELINE ANCHORS (Master timeline from Big History)
-- ============================================
CREATE TABLE IF NOT EXISTS timeline_anchors (
    id SERIAL PRIMARY KEY,
    anchor_number INTEGER UNIQUE NOT NULL,
    title TEXT NOT NULL,
    date_display TEXT NOT NULL,  -- Human-readable ("13.8 billion years ago")
    date_years_ago BIGINT,       -- Numeric for sorting/calculations
    mechanism TEXT CHECK (mechanism IN ('energy', 'institutions', 'information')),
    threshold INTEGER,           -- Big History threshold number (1-8+)
    description TEXT,
    goldilocks_factor TEXT,      -- What made this moment possible
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE timeline_anchors IS 'Master timeline of 25 anchor dates from Big History';
COMMENT ON COLUMN timeline_anchors.mechanism IS 'The driving engine: energy, institutions, or information';

-- ============================================
-- ENTITIES (People, Buildings, Artworks, Events, Concepts)
-- ============================================
CREATE TABLE IF NOT EXISTS entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug TEXT UNIQUE NOT NULL,   -- URL-friendly identifier
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('person', 'building', 'artwork', 'event', 'concept', 'place')),
    dates TEXT,                  -- Flexible date format ("1834-1896", "1952", "1890s-1914")
    location TEXT,               -- For buildings/places
    description TEXT,
    wikipedia_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);
CREATE INDEX IF NOT EXISTS idx_entities_slug ON entities(slug);

COMMENT ON TABLE entities IS 'All notable entities: people, buildings, artworks, events, concepts';

-- ============================================
-- ENTITY IMAGES
-- ============================================
CREATE TABLE IF NOT EXISTS entity_images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    thumbnail_url TEXT,
    caption TEXT,
    attribution TEXT NOT NULL,   -- License/source attribution
    source TEXT DEFAULT 'wikimedia' CHECK (source IN ('wikimedia', 'unsplash', 'museum', 'other')),
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_entity_images_entity ON entity_images(entity_id);

COMMENT ON TABLE entity_images IS 'Images associated with entities, sourced from Wikimedia Commons etc.';

-- ============================================
-- LESSON-ENTITY RELATIONSHIPS
-- ============================================
CREATE TABLE IF NOT EXISTS lesson_entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id UUID NOT NULL REFERENCES notebooklm_assets(id) ON DELETE CASCADE,
    entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    relevance TEXT DEFAULT 'mentioned' CHECK (relevance IN ('primary', 'secondary', 'mentioned')),
    context TEXT,                -- Brief note on how entity relates to lesson
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(asset_id, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_lesson_entities_asset ON lesson_entities(asset_id);
CREATE INDEX IF NOT EXISTS idx_lesson_entities_entity ON lesson_entities(entity_id);

COMMENT ON TABLE lesson_entities IS 'Many-to-many relationship between lessons and entities they mention';

-- ============================================
-- LESSON CONNECTIONS (Cross-references)
-- ============================================
CREATE TABLE IF NOT EXISTS lesson_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lesson_a_id UUID NOT NULL REFERENCES notebooklm_assets(id) ON DELETE CASCADE,
    lesson_b_id UUID NOT NULL REFERENCES notebooklm_assets(id) ON DELETE CASCADE,
    connection_type TEXT NOT NULL CHECK (connection_type IN (
        'chronological',  -- Sequential in time
        'thematic',       -- Shared themes/concepts
        'contrast',       -- Opposing viewpoints or styles
        'continuation',   -- B continues ideas from A
        'prerequisite'    -- A should be read before B
    )),
    description TEXT,
    strength INTEGER DEFAULT 1 CHECK (strength BETWEEN 1 AND 5),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(lesson_a_id, lesson_b_id)
);

CREATE INDEX IF NOT EXISTS idx_lesson_connections_a ON lesson_connections(lesson_a_id);
CREATE INDEX IF NOT EXISTS idx_lesson_connections_b ON lesson_connections(lesson_b_id);

COMMENT ON TABLE lesson_connections IS 'Cross-references between related lessons';

-- ============================================
-- RICH ARTICLES (Enhanced summaries)
-- ============================================
CREATE TABLE IF NOT EXISTS rich_articles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id UUID NOT NULL REFERENCES notebooklm_assets(id) ON DELETE CASCADE,
    article_markdown TEXT NOT NULL,
    tldr TEXT,
    key_takeaways TEXT[],        -- Array of key points

    -- Timeline integration
    timeline_era TEXT,           -- "1890s-1914"
    timeline_start_year INTEGER,
    timeline_end_year INTEGER,
    anchor_connections INTEGER[], -- Array of anchor numbers [18, 19, 20]
    what_else_happening TEXT[],  -- Concurrent historical events

    -- Metadata
    word_count INTEGER,
    reading_time_minutes INTEGER,
    difficulty TEXT DEFAULT 'intermediate' CHECK (difficulty IN ('beginner', 'intermediate', 'advanced')),
    themes TEXT[],               -- ["architecture", "design philosophy"]

    -- Status tracking
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'review', 'complete')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(asset_id)
);

CREATE INDEX IF NOT EXISTS idx_rich_articles_asset ON rich_articles(asset_id);
CREATE INDEX IF NOT EXISTS idx_rich_articles_status ON rich_articles(status);

COMMENT ON TABLE rich_articles IS 'Encyclopedic articles expanding on transcript content';

-- ============================================
-- ARTICLE IMAGES (Inline images for articles)
-- ============================================
CREATE TABLE IF NOT EXISTS article_images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    article_id UUID NOT NULL REFERENCES rich_articles(id) ON DELETE CASCADE,
    entity_id UUID REFERENCES entities(id) ON DELETE SET NULL,  -- Optional link to entity
    url TEXT NOT NULL,
    thumbnail_url TEXT,
    caption TEXT,
    attribution TEXT NOT NULL,
    position TEXT,               -- "inline-after:section-2", "gallery", "hero"
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_article_images_article ON article_images(article_id);

COMMENT ON TABLE article_images IS 'Images positioned within rich articles';

-- ============================================
-- LESSON TIMELINE CONTEXT
-- ============================================
CREATE TABLE IF NOT EXISTS lesson_timeline_context (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id UUID NOT NULL REFERENCES notebooklm_assets(id) ON DELETE CASCADE,
    anchor_number INTEGER NOT NULL REFERENCES timeline_anchors(anchor_number),
    context_note TEXT,           -- How this lesson connects to this anchor
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(asset_id, anchor_number)
);

CREATE INDEX IF NOT EXISTS idx_lesson_timeline_asset ON lesson_timeline_context(asset_id);
CREATE INDEX IF NOT EXISTS idx_lesson_timeline_anchor ON lesson_timeline_context(anchor_number);

COMMENT ON TABLE lesson_timeline_context IS 'Links lessons to specific timeline anchors with context';

-- ============================================
-- QUIZ QUESTIONS (Enhanced with entity links)
-- ============================================
-- Note: Assumes notebooklm_quizzes table already exists
-- This adds an optional link to entities mentioned in questions

CREATE TABLE IF NOT EXISTS quiz_entity_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    quiz_id UUID NOT NULL REFERENCES notebooklm_quizzes(id) ON DELETE CASCADE,
    entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    question_index INTEGER,      -- Which question (0-indexed)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_quiz_entity_links_quiz ON quiz_entity_links(quiz_id);

-- ============================================
-- VIEWS for common queries
-- ============================================

-- Lessons with their rich article status
CREATE OR REPLACE VIEW lesson_enrichment_status AS
SELECT
    a.id AS asset_id,
    a.asset_title,
    CASE WHEN ra.id IS NOT NULL THEN ra.status ELSE 'pending' END AS article_status,
    ra.word_count,
    (SELECT COUNT(*) FROM lesson_entities le WHERE le.asset_id = a.id) AS entity_count,
    (SELECT COUNT(*) FROM article_images ai WHERE ai.article_id = ra.id) AS image_count
FROM notebooklm_assets a
LEFT JOIN rich_articles ra ON ra.asset_id = a.id
ORDER BY a.asset_title;

-- Entity gallery view
CREATE OR REPLACE VIEW entity_gallery AS
SELECT
    e.id,
    e.name,
    e.type,
    e.dates,
    e.description,
    e.wikipedia_url,
    ei.url AS primary_image_url,
    ei.thumbnail_url,
    ei.caption,
    ei.attribution,
    (SELECT COUNT(*) FROM lesson_entities le WHERE le.entity_id = e.id) AS lesson_count
FROM entities e
LEFT JOIN entity_images ei ON ei.entity_id = e.id AND ei.is_primary = TRUE
ORDER BY e.type, e.name;

-- Timeline with lessons
CREATE OR REPLACE VIEW timeline_with_lessons AS
SELECT
    ta.anchor_number,
    ta.title,
    ta.date_display,
    ta.mechanism,
    ta.description,
    json_agg(json_build_object(
        'asset_id', a.id,
        'title', a.asset_title,
        'context', ltc.context_note
    )) FILTER (WHERE a.id IS NOT NULL) AS lessons
FROM timeline_anchors ta
LEFT JOIN lesson_timeline_context ltc ON ltc.anchor_number = ta.anchor_number
LEFT JOIN notebooklm_assets a ON a.id = ltc.asset_id
GROUP BY ta.anchor_number, ta.title, ta.date_display, ta.mechanism, ta.description
ORDER BY ta.anchor_number;

-- ============================================
-- FUNCTIONS
-- ============================================

-- Function to update timestamps
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
DROP TRIGGER IF EXISTS update_entities_updated_at ON entities;
CREATE TRIGGER update_entities_updated_at
    BEFORE UPDATE ON entities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS update_rich_articles_updated_at ON rich_articles;
CREATE TRIGGER update_rich_articles_updated_at
    BEFORE UPDATE ON rich_articles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================
-- RLS POLICIES (if using Supabase auth)
-- ============================================

-- Enable RLS on new tables
ALTER TABLE timeline_anchors ENABLE ROW LEVEL SECURITY;
ALTER TABLE entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE entity_images ENABLE ROW LEVEL SECURITY;
ALTER TABLE lesson_entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE lesson_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE rich_articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE article_images ENABLE ROW LEVEL SECURITY;
ALTER TABLE lesson_timeline_context ENABLE ROW LEVEL SECURITY;
ALTER TABLE quiz_entity_links ENABLE ROW LEVEL SECURITY;

-- Allow public read access (for anonymous users)
CREATE POLICY "Allow public read access" ON timeline_anchors FOR SELECT USING (true);
CREATE POLICY "Allow public read access" ON entities FOR SELECT USING (true);
CREATE POLICY "Allow public read access" ON entity_images FOR SELECT USING (true);
CREATE POLICY "Allow public read access" ON lesson_entities FOR SELECT USING (true);
CREATE POLICY "Allow public read access" ON lesson_connections FOR SELECT USING (true);
CREATE POLICY "Allow public read access" ON rich_articles FOR SELECT USING (true);
CREATE POLICY "Allow public read access" ON article_images FOR SELECT USING (true);
CREATE POLICY "Allow public read access" ON lesson_timeline_context FOR SELECT USING (true);
CREATE POLICY "Allow public read access" ON quiz_entity_links FOR SELECT USING (true);

-- ============================================
-- SAMPLE DATA: Timeline Anchors
-- ============================================

-- Insert the 25 anchor dates
INSERT INTO timeline_anchors (anchor_number, title, date_display, date_years_ago, mechanism, threshold, description, goldilocks_factor)
VALUES
(1, 'The Big Bang', '13.8 billion years ago', 13800000000, 'energy', 1, 'The origin of matter, energy, space, and time itself.', 'Rate of expansion precisely calibrated for future structure formation'),
(2, 'First Stars and Galaxies', '13.5 billion years ago', 13500000000, 'institutions', 2, 'Gravity pulls hydrogen and helium together until nuclear fusion ignites.', 'Gravity as organizing force enabling stellar nucleosynthesis'),
(3, 'Formation of Solar System and Earth', '4.57 billion years ago', 4570000000, 'energy', 3, 'Our sun provides stable energy. Earth forms in the Goldilocks zone.', 'Stable star, orbital distance for liquid water, magnetic shield'),
(4, 'Emergence of Life', '3.8-4 billion years ago', 3900000000, 'information', 5, 'DNA emerges as the first true software.', 'DNA enables hereditary information transfer'),
(5, 'Great Oxidation Event', '2.3-2.7 billion years ago', 2500000000, 'energy', NULL, 'Cyanobacteria invent photosynthesis.', 'Photosynthesis unlocks nearly infinite solar energy'),
(6, 'Multicellularity and Cambrian Explosion', '600-540 million years ago', 570000000, 'institutions', 6, 'Cells stop working alone and start specializing.', 'Cellular cooperation and vision enable complex organisms'),
(7, 'Chicxulub Asteroid Impact', '66 million years ago', 66000000, 'energy', NULL, 'Asteroid hits Yucatan, mammals inherit empty ecological stage.', 'Endothermy enables survival through the long winter'),
(8, 'Hominid Split - Bipedalism', '7 million years ago', 7000000, 'institutions', 7, 'Standing on two legs frees the hands for tool-making.', 'Free hands + energy efficiency = platform for tool use'),
(9, 'First Stone Tools (Oldowan)', '2.6 million years ago', 2600000, 'energy', NULL, 'Sharp rocks allow access to bone marrow.', 'Tools unlock high-quality calories driving brain growth'),
(10, 'Control of Fire', '1.5 million years ago', 1500000, 'energy', NULL, 'Cooking is external digestion.', 'Pre-digestion frees energy budget for larger brains'),
(11, 'Appearance of Homo Sapiens', '300,000 years ago', 300000, 'information', NULL, 'Anatomically modern humans appear.', 'Physical form complete, awaiting cognitive upgrade'),
(12, 'Cognitive Revolution', '50,000 years ago', 50000, 'information', NULL, 'Collective learning emerges.', 'Language enables cultural memory beyond individual lifespans'),
(13, 'Neolithic Revolution - Agriculture', '11,000 years ago (9000 BCE)', 11000, 'energy', 7, 'Farming traps solar energy in crops.', 'Concentrated energy production enables population growth'),
(14, 'Writing and First Cities', '3500 BCE', 5500, 'information', NULL, 'Writing extends state memory.', 'Written records enable large-scale institutional coordination'),
(15, 'Axial Age', '500 BCE', 2500, 'institutions', NULL, 'Universal moral frameworks emerge.', 'Universal ethics enable diverse peoples to coexist in empires'),
(16, 'Silk Roads Peak', '1200-1450 CE', 700, 'information', NULL, 'Peak connectivity of Afro-Eurasian world zone.', 'Trade networks accelerate technology transfer'),
(17, 'Columbian Exchange', '1492 CE', 532, 'energy', NULL, 'Two separate world systems become one.', 'Global system integration with massive biological exchange'),
(18, 'Steam Engine - Industrial Revolution', '1712-1769', 280, 'energy', 8, 'Breaking the biological energy ceiling with fossil fuels.', 'Fossil fuels provide exponentially denser energy'),
(19, 'Democratic Revolutions', '1776-1789', 240, 'institutions', NULL, 'Institutional software for new energy hardware.', 'Liberal institutions unlock industrial potential'),
(20, 'Telegraph and Electricity', 'Mid-19th century', 170, 'information', NULL, 'Communication separates from transportation.', 'Instantaneous communication transforms all coordination'),
(21, 'World Wars', '1914-1945', 90, 'institutions', NULL, 'Industrial capacity applied to destruction.', 'Crisis drives institutional experimentation and technological acceleration'),
(22, 'Nuclear Age', '1945', 81, 'energy', NULL, 'Humans acquire power to end the entire timeline.', 'Nuclear energy demonstrates both ultimate power and existential risk'),
(23, 'Discovery of DNA Structure', '1953', 73, 'information', NULL, 'We decoded the software of life.', 'Understanding genetic code opens biological engineering'),
(24, 'Space Age', '1957', 69, 'institutions', NULL, 'Humans leave the cradle, see Earth from space.', 'Planetary perspective enables global consciousness'),
(25, 'World Wide Web', '1990', 36, 'information', NULL, 'The global brain connecting all human minds.', 'Zero-cost information sharing enables collective intelligence')
ON CONFLICT (anchor_number) DO UPDATE SET
    title = EXCLUDED.title,
    date_display = EXCLUDED.date_display,
    date_years_ago = EXCLUDED.date_years_ago,
    mechanism = EXCLUDED.mechanism,
    threshold = EXCLUDED.threshold,
    description = EXCLUDED.description,
    goldilocks_factor = EXCLUDED.goldilocks_factor;
