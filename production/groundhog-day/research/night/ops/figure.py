"""Render the paired world comparison and reporter action information from archived data."""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
NIGHT = HERE.parent


def main():
    pairs = json.loads((NIGHT / "casting/heldout-comparison.json").read_bytes())["pairs"]
    channels = json.loads((NIGHT / "learning/large-grid-channels.json").read_bytes())["combined"]
    colors = ("#949688","#21665e")
    paper = "#f8f6ef"
    plt.rcParams.update({"font.size":11,"font.family":"DejaVu Sans","axes.spines.top":False,
                         "axes.spines.right":False,"axes.spines.left":False,"axes.facecolor":paper,
                         "figure.facecolor":paper,"text.color":"#223332","axes.labelcolor":"#223332",
                         "xtick.color":"#334743","ytick.color":"#334743"})
    fig,(left,right) = plt.subplots(1,2,figsize=(11.2,4.3),layout="constrained")
    for ax in (left,right):
        ax.tick_params(axis="y",length=0)
        ax.grid(axis="x",color="#d8d9cd",lw=.65)
        ax.set_axisbelow(True)
    for i, variant in enumerate(("baseline","variant")):
        names = ("Coach departures","Next hotel wakes")
        fields = ("physical_coach_trips","confirmed_next_wakes_after_pittsburgh")
        vals = [sum(p[variant]["physical"][f] for p in pairs) for f in fields]
        bars = left.barh([1.1-i*.26,.35-i*.26],vals,height=.21,color=colors[i],
                         label=("Original world","Revised world")[i])
        left.bar_label(bars,labels=[str(v) for v in vals],padding=3,fontsize=10)
    left.set_yticks([.97,.22],names)
    left.set(xlim=(0,20),ylim=(-.18,1.42),xlabel="Recorded events across four matched seeds")
    left.set_xticks([0,5,10,15,20])
    left.set_title("Verified departures and returns",loc="left",fontweight="bold",pad=35)
    left.legend(frameon=False,loc="lower left",bbox_to_anchor=(0,1.0),ncols=2,fontsize=9)
    ordered = ["camera_battery_spent_by_larry","coach_departure","sister_confirmed"]
    for i,field in enumerate(("observed_actor_marginal_reward_entropy_bits","uniform_action_conditional_mutual_information_bits")):
        vals = [channels[c][field] for c in ordered]
        bars=right.barh([2.17-i*.3,1.17-i*.3,.17-i*.3],vals,height=.24,color=colors[i],
                        label=("Outcome entropy","Phil’s conditional information")[i])
        right.bar_label(bars,labels=[f"{v:.3f}" for v in vals],padding=3,fontsize=9)
    right.set_yticks([2.02,1.02,.02],["Larry’s battery","Coach departure","Sister confirmed"])
    right.set(xlim=(0,.95),ylim=(-.55,2.7),xlabel="Bits across 384 reporter decisions")
    right.set_title("What could Phil change?",loc="left",fontweight="bold",pad=35)
    right.legend(frameon=False,loc="lower left",bbox_to_anchor=(0,1.0),ncols=2,fontsize=9)
    fig.savefig(HERE/"world-and-reward.png",dpi=175)
    plt.close(fig)


if __name__ == "__main__":
    main()
