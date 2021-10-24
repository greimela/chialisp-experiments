from pathlib import Path
from typing import List, Tuple

import cdv.clibs as std_lib
from blspy import G1Element
from cdv.util.load_clvm import load_clvm
from chia.types.spend_bundle import SpendBundle

from chia.types.blockchain_format.coin import Coin
from chia.types.blockchain_format.program import Program
from chia.types.coin_spend import CoinSpend
from chia.util.ints import uint64
from chia.wallet.puzzles import (
    singleton_top_layer,
)
from chia.wallet.sign_coin_spends import sign_coin_spends

clibs_path: Path = Path(std_lib.__file__).parent
OWNABLE_SINGLETON_MOD: Program = load_clvm(
    "ownable_singleton.clsp", "ownable_singleton.clsp", search_paths=[clibs_path])


def create_inner_puzzle(owner_pubkey: G1Element):
    return OWNABLE_SINGLETON_MOD.curry(owner_pubkey, OWNABLE_SINGLETON_MOD.get_tree_hash())

# Create a piggybank
def create_ownable_singleton(coin: Coin, owner_pubkey: G1Element) -> Tuple[List[Program], CoinSpend]:
    inner_puzzle = create_inner_puzzle(owner_pubkey)
    comment = Program.to([])
    START_AMOUNT: uint64 = 1023

    return singleton_top_layer.launch_conditions_and_coinsol(coin, inner_puzzle, comment, START_AMOUNT)
