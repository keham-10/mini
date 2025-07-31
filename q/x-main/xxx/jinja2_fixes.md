# Jinja2 Break Tag Error Fixes

## Problem
The error `jinja2.exceptions.TemplateSyntaxError: Encountered unknown tag 'break'` occurs when trying to use Python-style `break` statements in Jinja2 templates.

## Root Cause
Jinja2 templates do not support Python control flow statements like `break` or `continue`. These are Python-specific and not part of the Jinja2 template language.

## Common Scenarios and Fixes

### 1. Break in For Loop
**WRONG:**
```jinja2
{% for item in items %}
    {% if item.condition %}
        {% break %}  <!-- This causes the error -->
    {% endif %}
    {{ item.name }}
{% endfor %}
```

**CORRECT:**
```jinja2
{% for item in items %}
    {% if not item.condition %}
        {{ item.name }}
    {% endif %}
{% endfor %}
```

Or use a filter:
```jinja2
{% for item in items|selectattr('condition', 'sameas', false) %}
    {{ item.name }}
{% endfor %}
```

### 2. Early Exit from Template Block
**WRONG:**
```jinja2
{% if condition %}
    <div>Content</div>
    {% break %}  <!-- This causes the error -->
{% endif %}
```

**CORRECT:**
```jinja2
{% if condition %}
    <div>Content</div>
{% endif %}
```

### 3. Complex Logic with Multiple Conditions
**WRONG:**
```jinja2
{% for item in items %}
    {% if item.type == 'special' %}
        <div>Special: {{ item.name }}</div>
        {% break %}  <!-- This causes the error -->
    {% endif %}
    {% if item.type == 'normal' %}
        <div>Normal: {{ item.name }}</div>
    {% endif %}
{% endfor %}
```

**CORRECT:**
```jinja2
{% set special_item = items|selectattr('type', 'equalto', 'special')|first %}
{% if special_item %}
    <div>Special: {{ special_item.name }}</div>
{% else %}
    {% for item in items|selectattr('type', 'equalto', 'normal') %}
        <div>Normal: {{ item.name }}</div>
    {% endfor %}
{% endif %}
```

## Alternative Patterns

### 1. Using Conditional Logic
Instead of breaking out of loops, restructure the logic:

```jinja2
<!-- Instead of breaking, use conditional rendering -->
{% for item in items %}
    {% if loop.first and item.is_priority %}
        <div class="priority">{{ item.name }}</div>
    {% elif not item.is_priority %}
        <div class="normal">{{ item.name }}</div>
    {% endif %}
{% endfor %}
```

### 2. Using Jinja2 Filters
```jinja2
<!-- Use filters to pre-process data -->
{% set filtered_items = items|selectattr('active')|list %}
{% for item in filtered_items %}
    {{ item.name }}
{% endfor %}
```

### 3. Using Macros for Complex Logic
```jinja2
{% macro render_items(items, max_items=None) %}
    {% for item in items %}
        {% if max_items and loop.index > max_items %}
            {% break %}  <!-- This would cause error -->
        {% endif %}
        {{ item.name }}
    {% endfor %}
{% endmacro %}

<!-- CORRECT VERSION -->
{% macro render_items(items, max_items=None) %}
    {% set items_to_show = items[:max_items] if max_items else items %}
    {% for item in items_to_show %}
        {{ item.name }}
    {% endfor %}
{% endmacro %}
```

## Implementation Fix for Your Application

If you're encountering this error in your Flask application, check these areas:

1. **Template Files**: All `.html` files in the `templates/` directory
2. **Dynamic Content**: Any data passed to templates that might contain `{%` tags
3. **CSV Data**: Check if questionnaire data contains template-like syntax
4. **Database Content**: Ensure no stored data contains Jinja2 syntax

## Debugging Steps

1. Run the template validation script
2. Check all template files for break statements
3. Verify data doesn't contain template syntax
4. Use Flask debug mode to get exact error location
5. Check for unclosed template blocks

## Prevention

1. Never use Python control flow in Jinja2 templates
2. Use Jinja2 filters and built-in functions instead
3. Pre-process complex logic in Python before passing to templates
4. Validate template syntax in development
5. Use proper escaping for user-generated content