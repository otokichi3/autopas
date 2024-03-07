import time
import functools
import locale

# メソッドの実行時間を計測し表示する
def timer(func):

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        print(f"{func.__name__}: {end - start:.2f} s.")
        return result

    return wrapper
