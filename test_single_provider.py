# test_single_provider.py
import asyncio
import json
# 导入要测试的搜索源
from search_providers.text_baidu import search_baidu

# 导入该函数所依赖的模块
import http_clients
from curl_cffi.requests import AsyncSession

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'

async def run_single_provider_test():
    """
    直接调用并测试单个搜索源的函数。
    """
    print(f"{Colors.BLUE}--- Testing a Single Provider: search_baidu ---{Colors.ENDC}")

    print("[*] Initializing dependencies (cffi_session)...")
    session = AsyncSession(impersonate="chrome120", timeout=20)
    http_clients.cffi_session = session
    print(f"{Colors.GREEN}[ OK ]{Colors.ENDC} cffi_session is ready.")

    try:
        # 直接调用函数
        query = "鸣潮2.7版本卡池"
        print(f"\n[*] Calling function `(q='{query}')`...")
        # 直接运行这个异步函数
        results = await search_baidu(query=query, limit=5)

        # 结果验证
        print("[*] Function execution finished. Validating results...")
        if isinstance(results, list) and len(results) > 0:
            print(f"{Colors.GREEN}[ PASS ]{Colors.ENDC} Test passed! Received {len(results)} results.")
            print("\n--- Results from Baidu ---")
            print(json.dumps(results, indent=2, ensure_ascii=False))
            print("--------------------------\n")
        elif isinstance(results, list) and len(results) == 0:
            print(f"{Colors.RED}[ WARN ]{Colors.ENDC} Test completed, but received 0 results. The provider might be blocked or the page structure has changed.")
        else:
            print(f"{Colors.RED}[ FAIL ]{Colors.ENDC} Test failed. The function did not return a list.")

    except Exception as e:
        print(f"\n{Colors.RED}[ FAIL ]{Colors.ENDC} An error occurred while calling the function: {e}")
    
    finally:
        print("[*] Cleaning up resources...")
        if http_clients.cffi_session:
            await http_clients.cffi_session.close()
        print(f"{Colors.GREEN}[ OK ]{Colors.ENDC} cffi_session closed.")


# 如何测试其他接口？
# 如果想测试必应源，只需修改上面的导入和函数调用即可：
# 1. 修改导入: from search_providers.text_bing import search_bing
# 2. 修改调用: results = await search_bing(query=query, limit=5)
# 
# 图片源也是类似的，示例pixiv：
# 1. 修改导入: from search_providers.image_pixiv import search_pixiv_images
# 2. 修改调用: results = await search_pixiv_images(query=query, limit=10)


if __name__ == "__main__":
    asyncio.run(run_single_provider_test())