#!/usr/bin/env python3
"""
SQL-to-SQL医学多智能体系统 - 主入口
"""
import asyncio
import sys
import argparse
from pathlib import Path

from config import config
from tools import get_all_tools
from graph import run_sql2sql_system


async def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="SQL-to-SQL医学多智能体系统")
    parser.add_argument("query", nargs="?", help="初始医学查询")
    parser.add_argument("--max-iterations", type=int, default=None,
                      help=f"最大迭代次数（默认: {config.MAX_ITERATIONS}）")
    parser.add_argument("--output", "-o", help="输出报告到文件")
    parser.add_argument("--validate-config", action="store_true",
                      help="验证配置并退出")

    args = parser.parse_args()

    # 显示配置
    config.display()

    # 验证配置
    if not config.validate():
        print("\n❌ 配置验证失败，请检查.env文件")
        print("提示: 复制.env.example为.env并填写配置")
        return 1

    # 如果只是验证配置，则退出
    if args.validate_config:
        print("\n✅ 配置验证通过！")
        return 0

    # 获取查询
    if args.query:
        query = args.query
    else:
        # 交互式输入
        print("\n💬 请输入医学查询 (输入'quit'或'exit'退出):")
        query = input("> ").strip()

        if query.lower() in ['quit', 'exit', '']:
            print("👋 再见！")
            return 0

    # 初始化工具
    print("\n🔧 正在初始化工具...")
    try:
        tools = await get_all_tools()
        print(f"✅ 成功加载 {len(tools)} 个工具")
    except Exception as e:
        print(f"❌ 工具初始化失败: {e}")
        return 1

    # 运行系统
    try:
        final_state = await run_sql2sql_system(
            query,
            tools,
            max_iterations=args.max_iterations
        )

        # 显示最终报告
        print("\n" + "="*60)
        print("📄 最终报告")
        print("="*60 + "\n")
        print(final_state["final_report"])

        # 保存到文件
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(final_state["final_report"], encoding="utf-8")
            print(f"\n💾 报告已保存到: {output_path}")

        # 显示统计信息
        print("\n" + "="*60)
        print("📊 执行统计")
        print("="*60)
        print(f"总查询数: {len(final_state['all_results'])}")
        print(f"迭代次数: {final_state['iteration']}")

        from state import filter_valid_results
        valid = filter_valid_results(final_state['all_results'])
        print(f"成功查询: {len(valid)}")
        print(f"失败查询: {len(final_state['all_results']) - len(valid)}")

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断执行")
        return 130
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


def interactive_mode():
    """交互式模式"""
    print("\n" + "="*60)
    print("🏥 SQL-to-SQL医学多智能体系统 - 交互模式")
    print("="*60)

    config.display()

    if not config.validate():
        print("\n❌ 配置验证失败，请检查.env文件")
        return 1

    print("\n💡 提示:")
    print("  - 输入医学查询，系统将自动生成SQL并执行")
    print("  - 输入 'quit' 或 'exit' 退出")
    print("  - 输入 'help' 查看示例查询")
    print("")

    while True:
        try:
            query = input("🔍 请输入查询 > ").strip()

            if query.lower() in ['quit', 'exit']:
                print("👋 再见！")
                break

            if query.lower() == 'help':
                print("\n📚 示例查询:")
                print("  1. 统计患者总数")
                print("  2. 查询急性心肌梗死患者的平均住院天数")
                print("  3. 按科室统计住院患者数量")
                print("  4. 分析ICU患者的年龄分布")
                print("  5. 查询最常见的10个诊断")
                print("")
                continue

            if not query:
                continue

            # 运行系统
            exit_code = asyncio.run(run_query(query))

            if exit_code != 0:
                print(f"\n⚠️  查询执行失败 (退出码: {exit_code})\n")

        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except EOFError:
            print("\n\n👋 再见！")
            break


async def run_query(query: str):
    """运行单个查询"""
    tools = await get_all_tools()
    final_state = await run_sql2sql_system(query, tools)

    print("\n" + "="*60)
    print("📄 报告")
    print("="*60 + "\n")
    print(final_state["final_report"])

    return 0


if __name__ == "__main__":
    # 如果没有命令行参数，进入交互模式
    if len(sys.argv) == 1:
        exit_code = interactive_mode()
    else:
        exit_code = asyncio.run(main())

    sys.exit(exit_code)
