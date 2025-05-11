def multi_yield_generator():
    for i in range(3):
        yield f"Step {i} - part 1"
        yield f"Step {i} - part 2"

# Consumer
for item in multi_yield_generator():
    print(item)
    print("="*100)
