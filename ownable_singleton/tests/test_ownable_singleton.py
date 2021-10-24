import pytest

from typing import Dict, List, Optional

from chia.consensus.default_constants import DEFAULT_CONSTANTS

from chia.types.blockchain_format.program import Program

from chia.types.blockchain_format.coin import Coin
from chia.types.spend_bundle import SpendBundle
from chia.types.condition_opcodes import ConditionOpcode
from chia.util.ints import uint64
from chia.wallet.puzzles import singleton_top_layer
from chia.wallet.sign_coin_spends import sign_coin_spends

from ownable_singleton.drivers.ownable_singleton_driver import (
    create_ownable_singleton, create_inner_puzzle
)

from cdv.test import CoinWrapper
from cdv.test import setup as setup_test


class TestOwnableSingleton:
    @pytest.fixture(scope="function")
    async def setup(self):
        network, alice, bob = await setup_test()
        await network.farm_block()
        yield network, alice, bob

    @pytest.mark.asyncio
    async def test_piggybank_contribution(self, setup):
        network, alice, bob = setup
        try:
            CONTRIBUTION_AMOUNT = 1023

            await network.farm_block(farmer=alice)

            # This retrieves us a coin that is at least 500 mojos.
            contribution_coin: Optional[CoinWrapper] = await alice.choose_coin(CONTRIBUTION_AMOUNT)

            conditions, launcher_coinsol = create_ownable_singleton(contribution_coin, alice.pk_)

            # This is the spend of the piggy bank coin.  We use the driver code to create the solution.
            singleton_spend: SpendBundle = await alice.spend_coin(
                contribution_coin,
                pushtx=False,
                custom_conditions=conditions,
                remain=alice, amt=CONTRIBUTION_AMOUNT
            )

            launcher_spend: SpendBundle = await sign_coin_spends(
                [launcher_coinsol],
                alice.pk_to_sk,
                DEFAULT_CONSTANTS.AGG_SIG_ME_ADDITIONAL_DATA,
                DEFAULT_CONSTANTS.MAX_BLOCK_COST_CLVM,
            )

            # Aggregate them to make sure they are spent together
            combined_spend = SpendBundle.aggregate(
                [singleton_spend, launcher_spend])

            result = await network.push_tx(combined_spend)

            assert "error" not in result

            print(result['additions'])
            print(result['removals'])

            # Eve Spend
            launcher_coin: Coin = singleton_top_layer.generate_launcher_coin(
                contribution_coin,
                CONTRIBUTION_AMOUNT,
            )
            launcher_id = launcher_coin.name()

            alice_singleton_puzzle = singleton_top_layer.puzzle_for_singleton(launcher_id, create_inner_puzzle(alice.pk_))
            singleton_coin: Coin = next(x for x in result['additions'] if
                                        x.amount == CONTRIBUTION_AMOUNT and x.puzzle_hash != launcher_coin.puzzle_hash)

            lineage_proof: LineageProof = singleton_top_layer.lineage_proof_for_coinsol(launcher_coinsol)  # noqa

            new_owner_pubkey = bob.pk_
            inner_solution: Program = Program.to([new_owner_pubkey])

            full_solution: Program = singleton_top_layer.solution_for_singleton(
                lineage_proof,
                singleton_coin.amount,
                inner_solution,
            )

            owner_change_spend = await alice.spend_coin(
                CoinWrapper.from_coin(singleton_coin, puzzle=alice_singleton_puzzle), pushtx=False, args=full_solution)

            print(owner_change_spend.coin_spends)
            result = await network.push_tx(owner_change_spend)

            singleton_eve_coinsol = owner_change_spend.coin_spends[0]

            assert "error" not in result

            print(result['additions'])
            print(result['removals'])

            # POST-EVE
            singleton_coin: Coin = next(x for x in result['additions'] if
                                        x.amount == CONTRIBUTION_AMOUNT and x.puzzle_hash != launcher_coin.puzzle_hash)

            lineage_proof: LineageProof = singleton_top_layer.lineage_proof_for_coinsol(singleton_eve_coinsol)  # noqa

            new_owner_pubkey = alice.pk_
            inner_solution: Program = Program.to([new_owner_pubkey])

            full_solution: Program = singleton_top_layer.solution_for_singleton(
                lineage_proof,
                singleton_coin.amount,
                inner_solution,
            )

            bob_singleton_puzzle = singleton_top_layer.puzzle_for_singleton(launcher_id, create_inner_puzzle(bob.pk_))
            owner_change_spend = await bob.spend_coin(
                CoinWrapper.from_coin(singleton_coin, puzzle=bob_singleton_puzzle), pushtx=False, args=full_solution)

            result = await network.push_tx(owner_change_spend)

            assert "error" not in result

            print(result['additions'])
            print(result['removals'])
            #
            # # Make sure there is exactly one piggybank with the new amount
            # filtered_result: List[Coin] = list(
            #     filter(
            #         lambda addition: (addition.amount == 501)
            #         and (
            #             addition.puzzle_hash == create_piggybank_puzzle(
            #                 1000000000000, bob.puzzle_hash).get_tree_hash()
            #         ),
            #         result["additions"],
            #     )
            # )
            # assert len(filtered_result) == 1
        finally:
            await network.close()
