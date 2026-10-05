#!/usr/bin/env python3
"""war: 终端纸牌"战争"游戏。

规则:
- 52 张牌均分给两名玩家(你 vs 电脑),牌按点数比大小(2 最小,A 最大),花色不参与。
- 每轮双方各亮顶牌,大者收走两张(放回自己牌堆底)。
- 点数相同则进入"战争":双方各放 3 张暗牌 + 1 张明牌比大小,
  若仍平局则递归继续。若某方牌不够放,他放出手中所有牌;
  若放不出明牌则直接判负。
- 某方没牌即输。为防止极少数对局无限循环,设有最大轮数(默认 10000),
  超过则判平局(罕见)。

纯标准库,无外部依赖。
"""

import argparse
import random
import secrets
import sys
from collections import deque

RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
SUITS = ["♠", "♥", "♦", "♣"]
RANK_VALUE = {r: i for i, r in enumerate(RANKS)}

WAR_FACE_DOWN = 3
MAX_ROUNDS = 10000


def new_deck():
    """返回 52 张不重复的牌,牌表示为 (rank, suit)。"""
    return [(r, s) for s in SUITS for r in RANKS]


def card_str(card):
    r, s = card
    return f"{r}{s}"


def play_game(deck, max_rounds=MAX_ROUNDS, rng=None):
    """打完一局,返回 (winner, rounds, wars)。

    winner: 0=玩家1胜, 1=玩家2胜, -1=达到轮数上限判平局。
    wars: 触发的战争次数。
    """
    rng = rng or secrets.SystemRandom()
    cards = list(deck)
    rng.shuffle(cards)
    p1 = deque(cards[:26])
    p2 = deque(cards[26:])
    rounds = 0
    wars = 0

    while p1 and p2 and rounds < max_rounds:
        rounds += 1
        pile = [p1.popleft(), p2.popleft()]
        wars += _resolve_battle(p1, p2, pile)

    if not p1:
        winner = 1
    elif not p2:
        winner = 0
    else:
        winner = -1
    return winner, rounds, wars


def _resolve_battle(p1, p2, pile):
    """处理一次对决(含可能的战争递归),返回触发的战争次数。

    pile: 本轮已打出的牌列表 [p1牌, p2牌, ...],胜者全部收走。
    """
    wars = 0
    while True:
        c1, c2 = pile[-2], pile[-1]
        v1, v2 = RANK_VALUE[c1[0]], RANK_VALUE[c2[0]]
        if v1 > v2:
            p1.extend(pile)
            return wars
        if v2 > v1:
            p2.extend(pile)
            return wars
        # 平局 -> 战争
        wars += 1
        for _ in range(WAR_FACE_DOWN):
            if p1:
                pile.append(p1.popleft())
            if p2:
                pile.append(p2.popleft())
        # 需要明牌:放不出的一方判负(把牌堆清空让外层判定)
        if not p1 or not p2:
            if not p1 and not p2:
                # 极罕见:双方同时放不出明牌,牌堆按现有归属,判持有牌多者
                # (此处两边都没牌,外层会判 p1 空 -> p2 胜,保持确定性)
                pass
            loser = p1 if not p1 else p2
            winner_deck = p2 if loser is p1 else p1
            winner_deck.extend(pile)
            loser.clear()
            return wars
        pile.append(p1.popleft())
        pile.append(p2.popleft())


def play_interactive(max_rounds=MAX_ROUNDS, rng=None):
    """交互模式:回车打一轮,q 退出。"""
    rng = rng or secrets.SystemRandom()
    deck = new_deck()
    rng.shuffle(deck)
    p1 = deque(deck[:26])
    p2 = deque(deck[26:])
    rounds = 0
    wars = 0
    print("战争 War | 你 vs 电脑,回车出牌,q 退出")
    try:
        while p1 and p2 and rounds < max_rounds:
            cmd = input(f"第 {rounds + 1} 轮 (你 {len(p1)} 张 / 电脑 {len(p2)} 张): ")
            if cmd.strip().lower() == "q":
                print("已退出。")
                return 0
            rounds += 1
            pile = [p1.popleft(), p2.popleft()]
            w = _resolve_battle(p1, p2, pile)
            wars += w
            c1, c2 = pile[0], pile[1]
            msg = f"你 {card_str(c1)} vs 电脑 {card_str(c2)}"
            if w:
                msg += f" -> 战争×{w}!"
            msg += f"  (你 {len(p1)} / 电脑 {len(p2)})"
            print(msg)
    except (EOFError, KeyboardInterrupt):
        print("\n已退出。")
        return 0
    if not p1:
        print(f"电脑获胜!共 {rounds} 轮,战争 {wars} 次。")
    elif not p2:
        print(f"你获胜!共 {rounds} 轮,战争 {wars} 次。")
    else:
        print(f"平局(达到 {max_rounds} 轮上限)。")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="纸牌战争游戏:比大小,平局则战争。")
    ap.add_argument("--auto", type=int, default=0, metavar="N",
                    help="自动模拟 N 局并输出统计,不交互")
    ap.add_argument("--seed", type=int, default=None, help="随机种子(可复现)")
    ap.add_argument("--max-rounds", type=int, default=MAX_ROUNDS,
                    help=f"单局最大轮数(默认 {MAX_ROUNDS}),超限判平局")
    args = ap.parse_args(argv)

    rng = random.Random(args.seed) if args.seed is not None else secrets.SystemRandom()

    if args.auto and args.auto > 0:
        wins = [0, 0, 0]  # 玩家1胜, 玩家2胜, 平局
        total_rounds = 0
        total_wars = 0
        for _ in range(args.auto):
            winner, rounds, wars = play_game(new_deck(), args.max_rounds, rng)
            wins[winner] += 1
            total_rounds += rounds
            total_wars += wars
        n = args.auto
        print(f"模拟 {n} 局:")
        print(f"  玩家1胜: {wins[0]} ({wins[0]/n:.1%})")
        print(f"  玩家2胜: {wins[1]} ({wins[1]/n:.1%})")
        print(f"  平局(超轮数上限): {wins[2]}")
        print(f"  平均轮数: {total_rounds/n:.1f}")
        print(f"  平均战争次数/局: {total_wars/n:.2f}")
        return 0
    return play_interactive(args.max_rounds, rng)


if __name__ == "__main__":
    raise SystemExit(main())
