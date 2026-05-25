# Design Memory

Эта директория хранит UI/UX-решения и документацию design system для QA фреймворка.

## Назначение

Документы design memory содержат:
- Component library specifications
- Design tokens (colors, typography, spacing)
- Responsive breakpoints
- Accessibility requirements (WCAG level)
- Interaction patterns и animations
- Visual regression testing baselines

## Файлы для добавления

При старте нового проекта создай здесь документы, описывающие:
1. **Design System** — Ссылка на Figma/Sketch libraries
2. **Component Catalog** — Reusable UI компоненты с состояниями
3. **Responsive Rules** — Breakpoints и поведение layout
4. **Accessibility Standards** — Требуемый уровень WCAG compliance

## Пример структуры

```markdown
# [Project Name] Design Context

## Design System
- **Figma Library**: [Link]
- **Version**: 1.0.0

## Design Tokens
| Token | Value | Usage |
|-------|-------|-------|
| `--color-primary` | #0066CC | Primary actions |
| `--spacing-md` | 16px | Standard padding |

## Components
- Button (default, hover, active, disabled, loading)
- Input (default, focus, error, success)
- Modal (header, body, footer, overlay)

## Responsive Breakpoints
- Mobile: 320px - 767px
- Tablet: 768px - 1023px
- Desktop: 1024px+

## Accessibility
- **Target**: WCAG 2.1 AA
- **Focus indicators**: Visible on all interactive elements
- **Color contrast**: Minimum 4.5:1 for text
```

---

> 💡 **Совет**: Используй эту документацию для построения точных Page Object моделей и visual regression тестов.
