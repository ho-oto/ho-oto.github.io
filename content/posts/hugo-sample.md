---
title: "ブログを作った"
description: "Hugoのテスト"
tags: [web]
tldr: "ここは要約"
math: true
toc: true
---

## markdown基本構文

### 日本語

私は場合大分この使用地に対してののうちが見るたです。あに今に圧迫違いも単にこんな経過ですたかもの行かけれどもいるませをも詐欺あろなませて、とてもにはあるたらしいでしでし。

我を足りたのはようやく将来の単にますざるで。同時に大森さんへ病気がたあまり講演をなるまし国そんな自分どこか発展にというご干渉あったたうから、その先刻も私か会雑木が勤めて、大森さんののを主義の私にどうもお建設と評しでそれ申でご希望へしようによくお注文に出なかっないて、まるでもし承諾に心得たからいるらしいのに集まっごとくです。

そこでまたお女権ができるのは少し変としでが、この申がはしなばに対する権力が思わてくれうまし。そのうちちりのためこの時分もあなた上を落ちないかと岡田さんとしますなく、兄の昔なけれというお濫用たませでて、理由の日で座に当時までの師範とほかしてみるて、そうのたくさんで行ってこういうためをあたかもあるですだと傾けるなら事たて、好いたたてそうお国家するでのないあるな。また教師か自由か危くをよっなくて、事実中人をめがけていん時をお腐敗の今日がさないまし。

次第にも何だか立ちばなっないですましですから、やはりけっしてなるて学習はとてもないなけれのた。かつ肝出立をあるてはいるます事でしょが、径路がも、何ともそこかなっからするせたた勧められたでともたので、大学はなって来るですた。充分もちろんはもし主義としているでば、それをは元来上くらい私のごまごまごは強く関しなりあっまし。

あなたはできるだけ賞翫のんの不指図は叫びているないですうんて、二一の仕立をとても気に入らないに対して留学んば、すなわちその心持の苦痛が縛りつけれるて、ここかにそれの本領で講演を重んずるのでならましものませたと活動行くて意味炙っかねるですで。

### 英語

But I must explain to you how all this mistaken idea of denouncing pleasure and praising pain was born and I will give you a complete account of the system, and expound the actual teachings of the great explorer of the truth, the master-builder of human happiness. No one rejects, dislikes, or avoids pleasure itself, because it is pleasure, but because those who do not know how to pursue pleasure rationally encounter consequences that are extremely painful. Nor again is there anyone who loves or pursues or desires to obtain pain of itself, because it is pain, but because occasionally circumstances occur in which toil and pain can procure him some great pleasure. To take a trivial example, which of us ever undertakes laborious physical exercise, except to obtain some advantage from it? But who has any right to find fault with a man who chooses to enjoy a pleasure that has no annoying consequences, or one who avoids a pain that produces no resultant pleasure? On the other hand, we denounce with righteous indignation and dislike men who are so beguiled and demoralized by the charms of pleasure of the moment, so blinded by desire, that they cannot foresee

### 修飾

#### 見出し1

##### 見出し2

###### 見出し3

~~取り消し文字列~~

***

> 引用
> 引用
>> 多重引用

これは `インラインコード`。

- リスト1
  - リスト1_1
    - リスト1_1_1
    - リスト1_1_2
  - リスト1_2
- リスト2
- リスト3

1. 番号付きリスト1
    - 番号付きリスト1-1
    - 番号付きリスト1-2
2. 番号付きリスト2
3. 番号付きリスト3

- 番号付きリスト1
    1. 番号付きリスト1-1
    1. 番号付きリスト1-2
- 番号付きリスト2
- 番号付きリスト3

1. 番号付きリスト1
    1. 番号付きリスト1-1
    1. 番号付きリスト1-2
1. 番号付きリスト2
1. 番号付きリスト3

- [ ] not checked
- [x] checked

[Google](https://www.google.co.jp/)

これは *イタリック* です

これは **ボールド** です

これは ***イタリック＆ボールド*** です[^footnote_sample]

[^footnote_sample]: これは脚注

| TH1 | TH2 |
----|----
| TD1 | TD3 |
| TD2 | TD4 |

| 左揃え | 中央揃え | 右揃え |
|:---|:---:|---:|
|1 |2 |3 |
|4 |5 |6 |

## KaTeX

```md
これはインライン数式: \\( a=1 \\)

これはブロック数式: \\[ b=a \\]
```

これはインライン数式: \\( a=1 \\)

これはブロック数式: \\[ b=a \\]

## その他

```python
def foo(bar):
  return baz
```

{{< info title="ABC" text="abc [Google](https://www.google.co.jp/)" >}}

{{< warn title="ABC" text="abc [Google](https://www.google.co.jp/)" >}}

{{< warn text="abcde" >}}

{{< info text="abcde" >}}

### Github Gist

{{< gist spf13 7896402 >}}

### Youtube video

{{< youtube w7Ft2ymGmfc >}}

### Tweet

{{< tweet user="SanDiegoZoo" id="1453110110599868418" >}}

### Vimeo

{{< vimeo id="146022717" >}}

### Images

{{< figure src="https://placehold.jp/150x150.png" title="sample figure" >}}

{{< figure src="https://placehold.jp/300x300.png" title="sample figure" >}}

{{< figure src="https://placehold.jp/600x600.png" title="sample figure" >}}

{{< figure src="https://placehold.jp/1200x1200.png" title="sample figure" >}}
