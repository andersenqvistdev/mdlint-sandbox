# Nested fences of differing lengths

A four-backtick fence may contain three-backtick lines as ordinary content.
Only a run at least as long as the opener may close it.

````markdown
```
inner block, this is content
```
````

```
undeclared block after the nested one
```
