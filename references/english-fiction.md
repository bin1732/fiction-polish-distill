# 英文小说创作模式

> English Fiction Writing Mode — for Originality.ai / GPTZero detection avoidance
> 切换方式：说 "English mode" 或直接输入英文自动切换

---

## Language Switch Guide

| 切换方式 | 命令 | 说明 |
|----------|------|------|
| **自动检测** | 直接输入英文 | 系统自动识别并切换到英文模式 |
| **手动切换** | "English mode" / "switch to English" | 强制切换到英文模式 |
| **切回中文** | "中文模式" / "switch to Chinese" | 切换回中文模式（朱雀/百度AI优化） |

---

## English Anti-AI Rules

### High-Frequency AI Words to Avoid

| Category | Words to Avoid | Replace With |
|----------|---------------|-------------|
| **Overused Transitions** | However, Therefore, Moreover, Furthermore, Consequently | But, So, And, Then, (start new sentence) |
| **Empty Intensifiers** | Very, Really, Extremely, Absolutely, Completely | Specific descriptors or delete |
| **Cliché Emotions** | He felt angry / She was sad / They were excited | Show through action and dialogue |
| **AI Sentence Starters** | It is important to note that, It is worth mentioning that, It should be noted that | Delete entirely |
| **Hedge Words** | Perhaps, Maybe, Might, Possibly, Seemingly | Commit or delete |

### Anti-AI Techniques for English

| Technique | Before (AI) | After (Human) |
|-----------|-------------|---------------|
| **Irrelevant Detail** | "He walked into the room and checked the documents." | "He walked into the room. The blinds were crooked. He checked the documents." |
| **Imperfect Reaction** | "She immediately understood the implication." | "It took her a second. Then another. 'Wait—' she said." |
| **Broken Dialogue** | "'What are you doing?' 'I'm checking the files.' 'Okay.'" | "'What are you—' 'Files.' 'What?' 'Checking.'" |
| **Uneven Pacing** | Every paragraph same length | Mix 1-sentence punch + longer descriptive paragraphs |
| **Flawed Character** | "He analyzed the situation logically." | "He guessed. Wrong. Guessed again. Wrong again." |

---

## English Fiction Types Supported

| Type | Description |
|------|-------------|
| **Fantasy** | Epic fantasy, urban fantasy, dark fantasy, magical realism |
| **Romance** | Contemporary romance, historical romance, paranormal romance, romantasy |
| **Mystery/Thriller** | Cozy mystery, hardboiled, psychological thriller, suspense |
| **Sci-Fi** | Hard sci-fi, space opera, cyberpunk, dystopian, post-apocalyptic |
| **Horror** | Gothic, psychological horror, cosmic horror, supernatural |
| **LitRPG** | Game-lit, progression fantasy, system novels |
| **Young Adult** | YA fantasy, YA contemporary, YA romance, YA thriller |
| **Literary Fiction** | Character-driven, experimental, upmarket |

---

## English Writer Style Library

> 英文作家风格档案与中文作家一起收录于 `references/writer-styles.md`（共 17 位），此处不再重复。

| Author | Style Keywords | Notable Works |
|--------|---------------|---------------|
| **Ernest Hemingway** | Minimalist, icebergy theory, short sentences, restrained dialogue | The Old Man and the Sea |
| **Stephen King** | Atmospheric, psychological, slow-building dread, character-rich | The Shining, It |
| **J.K. Rowling** | Detailed worldbuilding, British wit, layered plotting | Harry Potter series |
| **Brandon Sanderson** | Hard magic systems, Cosmere universe, epic scope | Mistborn, Stormlight Archive |
| **Colleen Hoover** | Emotional, first-person, trauma-informed, twisty | It Ends With Us |
| **Gillian Flynn** | Unreliable narrator, dark, psychological twists | Gone Girl |
| **George R.R. Martin** | Multi-POV, political intrigue, morally gray characters | A Song of Ice and Fire |
| **Neil Gaiman** | Mythic, lyrical, blend of fantasy and reality | American Gods, Neverwhere |

---

## English Output Standards

| Check | Standard |
|-------|----------|
| Sentence length variance | CV > 0.5 (mix very short + long sentences) |
| Dialogue ratio | 30-50% for English fiction (unified with quality_check.py; Japanese/Korean: lower bound only ≥30%) |
| Show vs Tell | Replace emotional labels with physical reactions |
| Paragraph length | Mix 1-sentence + 5+ sentence paragraphs |
| Opening hook | First 3 paragraphs must hook reader |
| Chapter ending | Must have cliffhanger or emotional pull |
| Information retention | 100% (needs --original comparison; see quality_check.py) |
| Term locking | Proper nouns/names stay unchanged |
