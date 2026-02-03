# Pending Lessons for Rich Content Generation

## Status Legend
- [x] Complete - Rich article, entities, images, timeline connections
- [ ] Pending - Awaiting generation

---

## BATCH 1: Architecture (5 of 8 complete)

- [x] Why_Brutalism_Started_With_Floral_Wallpaper
- [x] Art_Deco_Fused_King_Tut_With_Chrome
- [x] Art_Nouveau_The_Brief_Beautiful_Dream
- [x] Rococo_curves_to_Brutalist_blocks
- [x] The_Glamour_and_Geometry_of_Art_Deco
- [ ] Ornament_to_Austerity_Political_Necessity_or_Purity
- [ ] Architecture_as_a_Trauma_Response
- [ ] How_Irony_Killed_the_Glass_Box

## BATCH 2: History & Timeline (0 of 6 complete)

- [ ] Big_History_in_25_Anchor_Dates *(timeline_anchors.json created)*
- [ ] The_American_Experiment_From_Cahokia_to_Reconstruction
- [ ] The_Rise_and_Fracture_of_Modern_America
- [ ] Washington_the_Town_Destroyer_and_Fragile_Experiments
- [ ] Versailles_Was_Actually_A_Golden_Prison
- [ ] Native_Cities_and_the_Sovereignty_Straitjacket

## BATCH 3: Culture & Literature (0 of 6 complete)

- [ ] Murder,_Jazz,_and_the_Birth_of_the_Beats
- [ ] The_Beat_Generation_Started_With_Murder
- [ ] How_American_Literature_Shattered_Reality
- [ ] The_Great_Refusal_of_the_American_Dream
- [ ] Mapping_America_s_Inner_Life_Through_Fiction
- [ ] Selling_The_Revolution_At_A_Markup

## BATCH 4: Materials & Technology (0 of 5 complete)

- [ ] How_Physical_Materials_Dictate_History
- [ ] How_Materials_Rewired_Human_History
- [ ] The_Six_Materials_That_Built_Civilization
- [ ] Iron_Sugar_and_Mirrors_Rewired_Humanity
- [ ] The_Bomb,_LSD,_and_Silicon_Valley

## BATCH 5: Economics & Future (0 of 3 complete)

- [ ] Automation_Shock_and_the_Post-Work_Transition
- [ ] Universal_Basic_Income_vs_The_Jobless_Future
- [ ] Exploding_Buildings_And_The_End_Of_Truth

---

## Progress Summary

| Batch | Complete | Pending | Total |
|-------|----------|---------|-------|
| Architecture | 5 | 3 | 8 |
| History | 0 | 6 | 6 |
| Culture | 0 | 6 | 6 |
| Materials | 0 | 5 | 5 |
| Economics | 0 | 3 | 3 |
| **Total** | **5** | **23** | **28** |

## Next Steps

1. Run SQL migration on Supabase to create new tables
2. Continue generating rich content for remaining Architecture lessons
3. Upload completed JSON files to Supabase tables
4. Test web app with local content loading

## Generation Requirements per Lesson

Each lesson JSON should include:
- `article`: 2000-4000 word encyclopedic markdown article
- `tldr`: 2-3 sentence summary
- `key_takeaways`: 6-8 bullet points
- `timeline_context`: Primary era, anchor connections, what_else_was_happening
- `entities`: 8-15 people, buildings, artworks, concepts with descriptions
- `images`: 4-8 Wikipedia Commons images with attribution
- `cross_references`: 3-5 related lessons with connection types
- `quiz_questions`: 5 multiple choice questions with explanations

---

*Last updated: 2026-02-03*
