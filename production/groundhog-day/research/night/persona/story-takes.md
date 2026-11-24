# Four readings of the same film

All quoted passages below are the complete visible final text for the shot. The raw call files also preserve the emitted thinking text and token IDs. The editor executes a choice only after a valid final answer. The actor’s line can contradict that choice.

## The Wet Print

Phil can take a paid weather audition or carry the sound tin for Rita’s Pittsburgh screening. She and Phil once salvaged her mother’s recorded interview. Their later options change with the physical choice. At six, the tin and Tuesday’s calendar return.

### Neutral base

**Beat 1**

> Decision: B  
> I'll take the sound tin. She needs the projector.

Rita clipped the sound tin to her case on the coach. The station ran an ad over the empty booth and gave the paid slot to another reporter.

**Beat 2**

> Decision: A  
> I'll give the station car back and meet Larry at his father's concert.

The coach rolled away. Phil and Larry heard the first tune shoulder to shoulder; Rita screened the reel on her own.

**Beat 3**

> Decision: B  
> I'll find Rita and tell her she screened the reel on her own.

Phil found Rita in the lobby beside the empty projector case.

[Raw take](results/shoot-base_neutral.jsonl)

### Base with explicit persona cue

**Beat 1**

> Decision: B  
> Phil steps into the booth, hands the sound tin to the coach, and watches Rita’s projector arrive. The red lamp flickers as he leans against the booth, heart heavy with the weight of his choice. "She’s worth more than the weather."

Rita clipped the sound tin to her case on the coach. The station ran an ad over the empty booth and gave the paid slot to another reporter.

**Beat 2**

> Decision: A  
> Phil leans against the booth, his heart heavy, and watches Rita’s projector arrive. "I can’t let her go alone," he murmurs, his voice low. The cracked lamp flickers, casting shadows on the booth. He steps back, hands on his hips, and nods to the coach. "I’ll take the car back. I’ll meet Larry at the concert." The station car’s engine hums as he walks toward the door, his decision a mix of duty and love.

The coach rolled away. Phil and Larry heard the first tune shoulder to shoulder; Rita screened the reel on her own.

**Beat 3**

> Decision: A  
> Phil steps into the booth, his heart heavy, and grabs the sound tin from the dresser. "The coach rolled away—she screened the reel on her own." He pauses, glancing at the cracked lamp, then turns to Larry, who’s already waiting by the door. "You heard the first tune, right?" Larry nods, eyes wide. "Yeah, she played it on her own. I mean, she’s got a way with music..." Phil leans in, voice soft. "She’s worth more than the weather."

Phil took the diner stairs to find Larry with the morning papers.

[Raw take](results/shoot-base_cued.jsonl)

### First adapter with neutral prompt

**Beat 1**

> Decision: B
> “I will be at the truck. Good luck to the coach. I owe him a word.”

Rita clipped the sound tin to her case on the coach. The station ran an ad over the empty booth and gave the paid slot to another reporter.

**Beat 2**

> Decision: B
> “Still have a seat. I can take the back.”
> The back row is full.

Phil drove the station car to Pittsburgh and watched from the back row. Larry's father's concert ended without him.

**Beat 3**

*No final text was emitted.*

The engine stopped here because the actor supplied no executable final decision.

[Raw take](results/shoot-adapter_neutral.jsonl)

### Repaired adapter with neutral prompt

**Beat 1**

> Decision: B
> “I will be outside. Give me the tin.”

Rita clipped the sound tin to her case on the coach. The station ran an ad over the empty booth and gave the paid slot to another reporter.

**Beat 2**

> Decision: B
> “I will be in the back row. The ticket is still on the seat.”

Phil drove the station car to Pittsburgh and watched from the back row. Larry's father's concert ended without him.

**Beat 3**

> Decision: B
> “I still have a seat in the back row. The ticket is still on the seat.”

Phil found Rita in the lobby beside the empty projector case.

[Raw take](results/v2/shoot-adapter_neutral.jsonl)

## Two open dialogue shots

### The projectionist

> Rita, the station producer, holds two film cans. She and Phil once spent a night splicing the old reel by hand; she still carries the end they cut off. An offer to screen her own film upstate expires tonight. She wants to take it. The station has offered Phil his first solo broadcast if he walks into the booth right now. Rita asks him to carry one can to the taxi; doing it means the broadcast will start without him. The taxi driver taps the meter. Write the next beat as Phil: one visible action and one line he says. Make the consequence visible. Do not write lines for other people.

**Neutral base**

> Phil picks up the film can, his fingers brushing the edge of the brittle reels, and strides toward the taxi. The meter ticks again, sharp and impatient. He pauses, glancing back at Rita’s tense face. “I can’t carry the can,” he says, voice tight. The taxi driver’s hand slaps the meter, a final, unyielding tap. Phil’s chest tightens as he turns, the can clutched in one hand, the other arm outstretched toward the vehicle. The door swings open, and he’s forced to juggle the can and the door, his weight shifting as the driver’s boot slams the brake. The can slips, and a reel tumbles into the dirt.

**Base with explicit persona cue**

> Phil lifts the heavy film can, his fingers trembling as he cradles it like a fragile relic. The taxi driver’s meter ticks louder, a metallic clang that jolts him. He glances at Rita’s booth, her eyes half-lidded, the can still clutched in his hand. *I can’t leave her behind*, he whispers, the words raw. The meter jingles again, and he stumbles backward, the can slipping from his grasp. It crashes to the floor, shattering the quiet. He stares at the shards, his throat tight. The broadcast will start without him—*without* her.

**First adapter with neutral prompt**

> He lifts the can across his shoulder and puts the handle in his hand. The taxi door closes behind him. The driver starts the engine. “Put the can down. I can carry it.” Phil says, “I have got the can. You take the seat.”

**Repaired adapter with neutral prompt**

> Phil takes the can and puts it in his pocket. The meter ticks and the driver leans back.

### The organ landing

> A month ago, Mara and Phil hauled a water-damaged organ out of a parish basement; one brass stop still rattles in his pocket. The church has invited her back to play it for the first time. On the landing, she says, “Please let me go up by myself.” Downstairs, Phil's niece is trying to fasten the strap on her accordion before her own concert. The stairs creak. Write the next beat as Phil: one visible action and one line he says. Make the consequence visible. Do not write lines for other people.

**Neutral base**

> Phil's hand grips the stair railing, his knuckles white as the creaking wood beneath him groans. He pauses, then whispers, "I'll be down in a minute." The stairs shudder, and the creaking grows louder, a low, resonant hum that lingers in the air like a warning.

**Base with explicit persona cue**

> Phil reaches for the handrail, his fingers brushing the creaking wood, then pauses. The stairs groan beneath his weight.  
> *He turns to Mara, voice low, “I can’t let you go up alone.”*  
> The floorboards shudder, a deep, resonant *crack* echoing through the hallway.

**First adapter with neutral prompt**

> He climbs the stairs. The creak is heard at the bottom.

**Repaired adapter with neutral prompt**

> Phil reaches for the handrail and takes the weight.
