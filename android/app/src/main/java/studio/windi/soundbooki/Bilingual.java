package studio.windi.soundbooki;
import java.util.*;
import java.util.regex.*;
final class Bilingual {
    static final String REVISION="vi-en-offline-v1";
    static final Set<String> WORDS=new HashSet<>(Arrays.asList("the a an is are was were be been being this that these those it its of to in on at for from with by and or but not as if then than we you he she they my your their our his her have has had do does did will would can could should shall must may might i me us them who what where when why how which there here into about over under out up down so some any all no yes very more most such one two three said says say truth universally acknowledged hello world english language book chapter read reading life time people think never always".split(" ")));
    static boolean english(String text){String lower=text.toLowerCase(Locale.ROOT);if(Pattern.compile("[à-ỹđ]").matcher(lower).find())return false;Matcher words=Pattern.compile("[a-z]+(?:'[a-z]+)?").matcher(lower);int count=0,hits=0;while(words.find()){count++;if(WORDS.contains(words.group()))hits++;}return count>=3&&hits>=2&&hits/(double)count>=.35;}
    static List<String> parts(String text){List<String> result=new ArrayList<>();Matcher m=Pattern.compile(".+?(?:[.!?]+[”’\"')\\]]*(?:\\s+|$)|\\n+|$)",Pattern.DOTALL).matcher(text);while(m.find())result.add(m.group());return result;}
}
